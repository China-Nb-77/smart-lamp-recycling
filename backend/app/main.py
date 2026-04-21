from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, File, Form, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from .config import AppSettings, load_settings
from .errors import ApplicationError, ServiceUnavailable, UnauthorizedError
from .llm import SiliconFlowAgent
from .models import (
    AddressRequest,
    AddressResponse,
    ClassifyPathRequest,
    CheckoutFormResponse,
    ConversationResponse,
    CreateOrderRequest,
    CreateQrRequest,
    CreateQrResponse,
    ElectronicOrderResponse,
    HealthDependency,
    HealthResponse,
    LampClassificationResponse,
    LogisticsMapResponse,
    LogisticsResponse,
    OrderView,
    PreflightCheck,
    PreflightResponse,
    QuotePathRequest,
    QuoteResponse,
    RecommendRequest,
    RecommendationResponse,
    RecommendationSelectRequest,
    RecommendationSelectResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionTimelineResponse,
    UserMessageRequest,
)
from .persistence import (
    EventRepository,
    OrderRepository,
    SessionStore,
    create_database_engine,
    create_redis_client,
    initialize_database,
)
from .security import SessionTokenManager
from .service import WorkflowService


@dataclass(slots=True)
class AppContext:
    settings: AppSettings
    redis_client: Any
    database_engine: Any
    service: WorkflowService


def build_context(settings: AppSettings | None = None) -> AppContext:
    loaded_settings = settings or load_settings()
    redis_client = create_redis_client(loaded_settings.redis_url)
    engine = create_database_engine(loaded_settings.database_url)
    initialize_database(engine)
    service = WorkflowService(
        settings=loaded_settings,
        sessions=SessionStore(redis_client, loaded_settings.session_ttl_seconds),
        orders=OrderRepository(engine),
        events=EventRepository(engine),
        tokens=SessionTokenManager(loaded_settings.session_secret),
        agent_brain=SiliconFlowAgent(loaded_settings),
    )
    return AppContext(
        settings=loaded_settings,
        redis_client=redis_client,
        database_engine=engine,
        service=service,
    )


def create_app(settings: AppSettings | None = None) -> FastAPI:
    context = build_context(settings)
    app = FastAPI(
        title="AI Light Workflow API",
        version="2.0.0",
        description="Hosted conversational workflow for lamp quote, recommendation and checkout.",
    )
    app.state.context = context
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(context.settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        try:
            response = await asyncio.wait_for(call_next(request), timeout=context.settings.request_timeout_seconds)
        except asyncio.TimeoutError:
            response = JSONResponse(
                status_code=504,
                content={
                    "code": "timeout",
                    "message": "request timed out",
                    "request_id": request_id,
                },
            )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": exc.errors()[0]["msg"] if exc.errors() else "validation error",
                "details": {"errors": exc.errors()},
                "request_id": getattr(request.state, "request_id", ""),
            },
        )

    def current_request_id(request: Request) -> str:
        return getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:12]}")

    def extract_session_token(request: Request) -> str:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        cookie_token = request.cookies.get(context.settings.session_cookie_name)
        if cookie_token:
            return cookie_token
        raise UnauthorizedError("missing session token")

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        redis_status = "ok"
        redis_detail = "connected"
        try:
            await run_in_threadpool(context.redis_client.ping)
        except Exception as exc:  # pragma: no cover - environment dependent
            redis_status = "error"
            redis_detail = str(exc)

        db_status = "ok"
        db_detail = "connected"
        try:
            def _db_ping():
                with context.database_engine.connect() as connection:
                    connection.execute(text("SELECT 1"))

            await run_in_threadpool(_db_ping)
        except Exception as exc:  # pragma: no cover - environment dependent
            db_status = "error"
            db_detail = str(exc)

        overall = "ok" if redis_status == "ok" and db_status == "ok" else "degraded"
        return HealthResponse(
            status=overall,
            request_id=current_request_id(request),
            dependencies={
                "redis": HealthDependency(status=redis_status, detail=redis_detail),
                "database": HealthDependency(status=db_status, detail=db_detail),
            },
            modes={
                "workflow": context.settings.workflow_mode,
                "payment": context.settings.payment_mode,
            },
        )

    @app.get("/preflight", response_model=PreflightResponse)
    async def preflight(request: Request) -> PreflightResponse:
        quote_ready, quote_reason = await run_in_threadpool(context.service.preflight_quote)
        classifier_ready, classifier_reason = await run_in_threadpool(context.service.preflight_classifier)
        recommendation_ready, recommendation_reason = await run_in_threadpool(context.service.preflight_recommendation)
        payment_ready, payment_reason = await run_in_threadpool(context.service.preflight_payment)
        return PreflightResponse(
            request_id=current_request_id(request),
            quote=PreflightCheck(ready=quote_ready, reason=quote_reason),
            classifier=PreflightCheck(ready=classifier_ready, reason=classifier_reason),
            recommendation=PreflightCheck(ready=recommendation_ready, reason=recommendation_reason),
            payment=PreflightCheck(ready=payment_ready, reason=payment_reason),
        )

    @app.post("/agent/sessions", response_model=SessionCreateResponse)
    async def create_session(payload: SessionCreateRequest, request: Request, response: Response) -> SessionCreateResponse:
        result = await run_in_threadpool(
            context.service.create_session,
            user_id=payload.user_id,
            client_session_id=payload.client_session_id,
            request_id=current_request_id(request),
        )
        response.set_cookie(
            key=context.settings.session_cookie_name,
            value=result.session_token,
            httponly=True,
            samesite="lax",
            max_age=context.settings.session_ttl_seconds,
        )
        return result

    @app.get("/agent/sessions/{session_id}/timeline", response_model=SessionTimelineResponse)
    async def get_timeline(session_id: str, request: Request) -> SessionTimelineResponse:
        token = extract_session_token(request)
        return await run_in_threadpool(context.service.get_timeline, session_id=session_id, token=token)

    @app.post("/agent/sessions/{session_id}/image", response_model=ConversationResponse)
    async def upload_session_image(session_id: str, request: Request, file: UploadFile = File(...)) -> ConversationResponse:
        token = extract_session_token(request)
        raw = await file.read()
        return await run_in_threadpool(
            context.service.upload_old_lamp,
            session_id=session_id,
            token=token,
            raw=raw,
            filename=file.filename or "upload.png",
            content_type=file.content_type or "",
            request_id=current_request_id(request),
        )

    @app.post("/agent/sessions/{session_id}/messages", response_model=ConversationResponse)
    async def send_message(session_id: str, payload: UserMessageRequest, request: Request) -> ConversationResponse:
        token = extract_session_token(request)
        return await run_in_threadpool(
            context.service.handle_user_message,
            session_id=session_id,
            token=token,
            text=payload.text,
            request_id=current_request_id(request),
        )

    @app.post("/agent/sessions/{session_id}/preferences", response_model=ConversationResponse)
    async def submit_preferences(session_id: str, payload: dict[str, Any], request: Request) -> ConversationResponse:
        token = extract_session_token(request)
        return await run_in_threadpool(
            context.service.submit_preferences,
            session_id=session_id,
            token=token,
            payload=payload,
            request_id=current_request_id(request),
        )

    @app.post("/agent/sessions/{session_id}/recommendations/select", response_model=RecommendationSelectResponse)
    async def select_recommendation(session_id: str, payload: RecommendationSelectRequest, request: Request) -> RecommendationSelectResponse:
        token = extract_session_token(request)
        return await run_in_threadpool(
            context.service.select_recommendation,
            session_id=session_id,
            token=token,
            sku_id=payload.sku_id,
            request_id=current_request_id(request),
        )

    @app.get("/agent/forms/checkout", response_model=CheckoutFormResponse)
    async def get_checkout_form(request: Request, session_id: str = Query(...)) -> CheckoutFormResponse:
        token = extract_session_token(request)
        return await run_in_threadpool(context.service.get_checkout_form, session_id=session_id, token=token)

    @app.post("/agent/addresses/normalize", response_model=AddressResponse)
    async def normalize_address(payload: AddressRequest) -> AddressResponse:
        return await run_in_threadpool(context.service.normalize_address, payload.model_dump())

    @app.post("/agent/addresses/locate", response_model=AddressResponse)
    async def locate_address(payload: AddressRequest) -> AddressResponse:
        return await run_in_threadpool(context.service.locate_address, payload.model_dump())

    @app.post("/agent/orders", response_model=OrderView)
    async def create_order(payload: CreateOrderRequest, request: Request) -> OrderView:
        token = extract_session_token(request)
        return await run_in_threadpool(
            context.service.create_order,
            payload=payload,
            token=token,
            request_id=current_request_id(request),
        )

    @app.get("/agent/orders/{order_id}", response_model=OrderView)
    async def get_order(order_id: str, sync: bool = Query(True)) -> OrderView:
        return await run_in_threadpool(context.service.get_order, order_id=order_id, sync=sync)

    @app.post("/agent/orders/{order_id}/qr", response_model=CreateQrResponse)
    async def create_qr(order_id: str, payload: CreateQrRequest, request: Request) -> CreateQrResponse:
        app_origin = request.headers.get("Origin") or f"http://{request.headers.get('host', 'localhost:5173')}"
        return await run_in_threadpool(
            context.service.create_qr,
            order_id=order_id,
            payload=payload,
            app_origin=app_origin,
            request_id=current_request_id(request),
        )

    @app.get("/agent/orders/{order_id}/electronic", response_model=ElectronicOrderResponse)
    async def get_electronic_order(order_id: str, qrToken: str = Query(...)) -> ElectronicOrderResponse:
        return await run_in_threadpool(context.service.get_electronic_order, order_id=order_id, qr_token=qrToken)

    @app.get("/agent/orders/{order_id}/logistics", response_model=LogisticsResponse)
    async def get_logistics(order_id: str) -> LogisticsResponse:
        return await run_in_threadpool(context.service.get_logistics, order_id=order_id)

    @app.get("/agent/orders/{order_id}/logistics-map", response_model=LogisticsMapResponse)
    async def get_logistics_map(order_id: str) -> LogisticsMapResponse:
        return await run_in_threadpool(context.service.get_logistics_map, order_id=order_id)

    @app.post("/quote", response_model=QuoteResponse)
    async def quote_by_path(payload: QuotePathRequest, request: Request) -> QuoteResponse:
        path = await run_in_threadpool(context.service.resolve_image_path, payload.image_path)
        return await run_in_threadpool(context.service.quote_image, image_path=path, request_id=current_request_id(request))

    @app.post("/quote-upload", response_model=QuoteResponse)
    async def quote_upload(request: Request, file: UploadFile = File(...)) -> QuoteResponse:
        raw = await file.read()
        upload_path, upload = await run_in_threadpool(
            context.service.store_upload,
            raw=raw,
            filename=file.filename or "upload.png",
            content_type=file.content_type or "",
        )
        response = await run_in_threadpool(context.service.quote_image, image_path=upload_path, request_id=current_request_id(request))
        response.upload = upload
        return response

    @app.post("/recommend", response_model=RecommendationResponse)
    async def recommend(payload: RecommendRequest) -> RecommendationResponse:
        return await run_in_threadpool(
            context.service.recommend,
            reference_sku_id=payload.reference_sku_id,
            preferences=payload.preferences,
        )

    @app.post("/classify-lamp", response_model=LampClassificationResponse)
    async def classify_by_path(payload: ClassifyPathRequest, request: Request) -> LampClassificationResponse:
        path = await run_in_threadpool(context.service.resolve_image_path, payload.image_path)
        return await run_in_threadpool(
            context.service.classify_path,
            image_path=path,
            request_id=current_request_id(request),
            candidate_labels=payload.candidate_labels,
            topk=payload.topk,
        )

    @app.post("/classify-lamp-upload", response_model=LampClassificationResponse)
    @app.post("/classify-upload", response_model=LampClassificationResponse)
    @app.post("/classify", response_model=LampClassificationResponse)
    async def classify_upload(
        request: Request,
        file: UploadFile = File(...),
        candidate_labels: str | None = Form(default=None),
        topk: int = Form(default=3),
    ) -> LampClassificationResponse:
        raw = await file.read()
        labels = None
        if candidate_labels:
            labels = [item.strip() for item in candidate_labels.split(",") if item.strip()]
        return await run_in_threadpool(
            context.service.classify_upload,
            raw=raw,
            filename=file.filename or "upload.png",
            content_type=file.content_type or "",
            request_id=current_request_id(request),
            candidate_labels=labels,
            topk=topk,
        )

    @app.get("/catalog-image")
    async def catalog_image(path: str = Query(...)) -> FileResponse:
        resolved = await run_in_threadpool(context.service.resolve_image_path, path)
        if not resolved.is_file():
            raise ApplicationError("image not found", details={"path": path})
        media_type = mimetype = None
        guessed = __import__("mimetypes").guess_type(resolved.name)[0]
        if guessed:
            mimetype = guessed
        return FileResponse(resolved, media_type=mimetype)

    return app


app = create_app()


def serve_api(host: str = "127.0.0.1", port: int = 8000, config_dir: str | None = None) -> None:
    import uvicorn

    settings = load_settings()
    if config_dir:
        settings.config_dir = settings.base_dir / config_dir
    uvicorn.run(create_app(settings), host=host, port=port)
