from __future__ import annotations

import io
import json
import mimetypes
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from PIL import Image, UnidentifiedImageError

from image_quote_system.classification.lamp_type import DEFAULT_LAMP_LABELS, OpenSourceLampTypeClassifier
from image_quote_system.config import load_config
from image_quote_system.data.catalog import load_catalog

from .adapters.ecommerce import EcommerceSearchAdapter, build_taobao_search_url
from .config import AppSettings
from .errors import ConflictError, LLMFormatError, NotFoundError, ServiceUnavailable, UnauthorizedError
from .llm import LLMDecision, SiliconFlowAgent
from .models import (
    AddressResponse,
    CardEnvelope,
    CheckoutDraft,
    CheckoutFormField,
    CheckoutFormResponse,
    CheckoutFormSchema,
    CheckoutFormSummary,
    ConversationMessage,
    ConversationResponse,
    CreateOrderRequest,
    CreateQrRequest,
    CreateQrResponse,
    ElectronicOrderResponse,
    FollowUpOption,
    FollowUpQuestion,
    LampClassificationResponse,
    LogisticsMapResponse,
    LogisticsResponse,
    OrderView,
    QuoteResponse,
    QuoteSummary,
    RecommendationResponse,
    RecommendationSelectResponse,
    SessionCreateResponse,
    SessionState,
    SessionTimelineResponse,
    Stage,
    TimelineEvent,
    TRANSITIONS,
    UploadInfo,
)
from .persistence import EventRepository, OrderRepository, SessionStore, utc_now
from .security import SessionTokenManager


FOLLOW_UP_QUESTIONS = [
    FollowUpQuestion(
        id="space",
        question="主要安装在哪个空间？",
        options=[
            FollowUpOption(value="living_room", label="客厅"),
            FollowUpOption(value="bedroom", label="卧室"),
            FollowUpOption(value="dining_room", label="餐厅"),
            FollowUpOption(value="office", label="办公室"),
        ],
    ),
    FollowUpQuestion(
        id="budget_level",
        question="预算更偏向哪一档？",
        options=[
            FollowUpOption(value="economy", label="经济"),
            FollowUpOption(value="balanced", label="均衡"),
            FollowUpOption(value="premium", label="高端"),
        ],
    ),
    FollowUpQuestion(
        id="install_type",
        question="偏好换成哪种类型？",
        options=[
            FollowUpOption(value="pendant", label="吊灯"),
            FollowUpOption(value="wall", label="壁灯"),
            FollowUpOption(value="floor", label="落地灯"),
            FollowUpOption(value="any", label="都可以"),
        ],
    ),
]


FORM_SCHEMA = CheckoutFormSchema(
    title="收货信息",
    submit_label="生成支付二维码",
    fields=[
        CheckoutFormField(
            key="name",
            label="收货人姓名",
            component="input",
            type="text",
            required=True,
            placeholder="请输入收货人姓名",
        ),
        CheckoutFormField(
            key="phone",
            label="联系电话",
            component="input",
            type="tel",
            required=True,
            placeholder="请输入联系电话",
        ),
        CheckoutFormField(
            key="full_address",
            label="详细地址",
            component="textarea",
            required=True,
            action="locate",
            placeholder="请输入完整收货地址",
        ),
    ],
)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WorkflowService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        sessions: SessionStore,
        orders: OrderRepository,
        events: EventRepository,
        tokens: SessionTokenManager,
        agent_brain: SiliconFlowAgent,
        ecommerce: EcommerceSearchAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.sessions = sessions
        self.orders = orders
        self.events = events
        self.tokens = tokens
        self.agent_brain = agent_brain
        self.ecommerce = ecommerce or EcommerceSearchAdapter()
        self._catalog_cache: list[dict[str, Any]] | None = None
        self._classifier: OpenSourceLampTypeClassifier | None = None

    def create_session(
        self,
        *,
        user_id: str | None,
        client_session_id: str | None,
        request_id: str,
    ) -> SessionCreateResponse:
        now = utc_now()
        expires_at = now + timedelta(seconds=self.settings.session_ttl_seconds)
        session = SessionState(
            session_id=f"sess_{uuid.uuid4().hex[:20]}",
            user_id=(user_id or f"guest_{uuid.uuid4().hex[:12]}"),
            client_session_id=client_session_id,
            stage=Stage.INIT,
            created_at=now,
            updated_at=now,
            token_expires_at=expires_at,
        )
        self.sessions.save(session)
        token = self.tokens.issue(
            session_id=session.session_id,
            user_id=session.user_id,
            client_session_id=session.client_session_id,
            expires_at_epoch=int(expires_at.timestamp()),
        )
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            event_type="session_created",
            payload={"user_id": session.user_id, "client_session_id": session.client_session_id},
        )
        return SessionCreateResponse(
            session_id=session.session_id,
            session_token=token,
            user_id=session.user_id,
            expires_at=expires_at,
            state=session.stage,
            messages=[],
        )

    def get_timeline(self, *, session_id: str, token: str) -> SessionTimelineResponse:
        self.require_session(session_id=session_id, token=token)
        return SessionTimelineResponse(session_id=session_id, events=self.events.list_by_session(session_id))

    def llm_decide(
        self,
        *,
        session: SessionState,
        user_text: str,
        request_id: str,
        interaction: str,
    ) -> LLMDecision:
        context = self._build_llm_context(session=session, user_text=user_text, interaction=interaction)
        decision = self.agent_brain.decide(
            messages=[*session.conversation_history, {"role": "user", "content": user_text}],
            context=context,
            prompt_version=f"siliconflow.{interaction}.v1",
        )
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            order_id=session.order_id,
            event_type="llm_decision",
            payload={"llm": decision.trace, "decision": {
                "reply": decision.reply,
                "intent": decision.intent,
                "confidence": decision.confidence,
                "slots": decision.slots,
            }},
        )
        return decision

    def _build_llm_context(
        self,
        *,
        session: SessionState,
        user_text: str,
        interaction: str,
    ) -> dict[str, Any]:
        quote_summary = ((session.quote_payload or {}).get("summary") or {}) if session.quote_payload else {}
        recommendation_payload = session.recommendation_payload or {}
        return {
            "interaction": interaction,
            "stage": session.stage.value,
            "user_input": user_text,
            "has_quote": bool(session.quote_payload),
            "quote_summary": quote_summary,
            "preferences": session.preferences,
            "has_recommendations": bool(recommendation_payload.get("recommendations")),
            "recommendation_count": len(recommendation_payload.get("recommendations") or []),
            "selected_recommendation": session.selected_recommendation,
            "requires_review": session.requires_review,
            "review_reasons": session.review_reasons,
            "can_checkout": bool(session.selected_recommendation) and not session.requires_review,
            "order_id": session.order_id,
        }

    def _append_history(self, session: SessionState, *, role: str, content: str) -> None:
        text = str(content or "").strip()
        if not text:
            return
        session.conversation_history.append({"role": role, "content": text})
        session.conversation_history = session.conversation_history[-12:]

    def _normalize_llm_slots(self, slots: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        room = self._normalize_room(slots.get("room") or slots.get("space"))
        if room:
            normalized["space"] = room

        install_type = self._normalize_install_type(slots.get("install_type") or slots.get("lamp_type") or slots.get("type"))
        if install_type:
            normalized["install_type"] = install_type

        budget_level = self._normalize_budget_level(slots.get("budget_level"))
        budget = slots.get("budget")
        if budget_level:
            normalized["budget_level"] = budget_level
        elif budget not in (None, ""):
            try:
                normalized["budget_level"] = self._budget_level_from_amount(float(budget))
            except (TypeError, ValueError):
                pass

        material = self._normalize_material(slots.get("material"))
        if material:
            normalized["material"] = material

        note = str(slots.get("note") or "").strip()
        if note:
            normalized["note"] = note
        return normalized

    def _normalize_room(self, value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        mapping = {
            "客厅": "living_room",
            "living_room": "living_room",
            "living room": "living_room",
            "卧室": "bedroom",
            "bedroom": "bedroom",
            "餐厅": "dining_room",
            "饭厅": "dining_room",
            "dining_room": "dining_room",
            "dining room": "dining_room",
            "办公室": "office",
            "办公": "office",
            "office": "office",
            "门店": "store",
            "商铺": "store",
            "store": "store",
        }
        return mapping.get(raw)

    def _normalize_install_type(self, value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        mapping = {
            "吊灯": "pendant",
            "pendant": "pendant",
            "chandelier": "pendant",
            "壁灯": "wall",
            "墙灯": "wall",
            "wall": "wall",
            "wall lamp": "wall",
            "落地灯": "floor",
            "地灯": "floor",
            "floor": "floor",
            "floor lamp": "floor",
            "都可以": "any",
            "随意": "any",
            "any": "any",
        }
        return mapping.get(raw)

    def _normalize_budget_level(self, value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        mapping = {
            "经济": "economy",
            "economy": "economy",
            "budget": "economy",
            "便宜": "economy",
            "均衡": "balanced",
            "balanced": "balanced",
            "中等": "balanced",
            "高端": "premium",
            "premium": "premium",
            "豪华": "premium",
        }
        return mapping.get(raw)

    def _normalize_material(self, value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        mapping = {
            "玻璃": "glass",
            "glass": "glass",
            "铝": "aluminum",
            "aluminum": "aluminum",
            "黄铜": "brass",
            "brass": "brass",
            "都可以": "any",
            "any": "any",
        }
        return mapping.get(raw)

    def _budget_level_from_amount(self, amount: float) -> str:
        if amount <= 500:
            return "economy"
        if amount >= 2000:
            return "premium"
        return "balanced"

    def classify_upload(
        self,
        *,
        raw: bytes,
        filename: str,
        content_type: str,
        request_id: str,
        candidate_labels: list[str] | None = None,
        topk: int = 3,
    ) -> LampClassificationResponse:
        upload_path, upload = self.store_upload(raw=raw, filename=filename, content_type=content_type)
        result = self.classify_path(
            image_path=upload_path,
            request_id=request_id,
            candidate_labels=candidate_labels,
            topk=topk,
        )
        result.upload = upload
        return result

    def classify_path(
        self,
        *,
        image_path: Path,
        request_id: str,
        candidate_labels: list[str] | None = None,
        topk: int = 3,
    ) -> LampClassificationResponse:
        ready, reason = self.preflight_classifier()
        labels = candidate_labels or list(DEFAULT_LAMP_LABELS)
        if not ready:
            if not self.settings.allow_review_fallback:
                raise ServiceUnavailable("model not ready", details={"reason": reason})
            fallback = LampClassificationResponse(
                success=False,
                lamp_type=labels[0],
                confidence=0.0,
                label=labels[0],
                score=0.0,
                candidates=[{"label": labels[0], "score": 0.0}],
                model_id="manual-review",
                backend="review-fallback",
                image_path=str(image_path),
                requires_review=True,
                review_reasons=[reason],
            )
            self.record_event(
                request_id=request_id,
                event_type="classification_review_fallback",
                payload=fallback.model_dump(),
            )
            return fallback

        classifier = self._get_classifier()
        image = Image.open(image_path).convert("RGB")
        raw = classifier._classify_with_model(image, labels)
        normalized = classifier._normalize_predictions(raw)[: max(int(topk), 1)]
        if not normalized:
            raise ServiceUnavailable("model not ready", details={"reason": "classifier returned no predictions"})
        best = normalized[0]
        result = LampClassificationResponse(
            success=True,
            lamp_type=str(best["label"]),
            confidence=float(best["score"]),
            label=str(best["label"]),
            score=float(best["score"]),
            candidates=normalized,
            model_id=classifier.model_id,
            backend=classifier.backend,
            image_path=str(image_path),
        )
        self.record_event(
            request_id=request_id,
            event_type="classification_completed",
            payload=result.model_dump(),
        )
        return result

    def upload_old_lamp(
        self,
        *,
        session_id: str,
        token: str,
        raw: bytes,
        filename: str,
        content_type: str,
        request_id: str,
    ) -> ConversationResponse:
        session = self.require_session(session_id=session_id, token=token)
        upload_path, upload_info = self.store_upload(raw=raw, filename=filename, content_type=content_type)
        quote_payload = self.quote_image(image_path=upload_path, request_id=request_id)
        quote_payload.upload = upload_info

        session.quote_payload = quote_payload.model_dump()
        session.preferences = {
            key: value
            for key, value in session.preferences.items()
            if key in {"install_type", "space", "budget_level", "note"}
        }
        session.recommendation_payload = None
        session.selected_recommendation = None
        session.order_id = None
        session.requires_review = quote_payload.summary.requires_review
        session.review_reasons = list(quote_payload.summary.review_reasons)
        session.updated_at = utc_now()
        self.transition(session, Stage.QUOTE_DONE)
        decision = self.llm_decide(
            session=session,
            user_text="用户刚上传了一张旧灯图片，请继续对话。",
            request_id=request_id,
            interaction="image_upload",
        )
        normalized_slots = self._normalize_llm_slots(decision.slots)
        if normalized_slots:
            session.preferences.update(normalized_slots)
        self._append_history(session, role="assistant", content=decision.reply)
        self.sessions.save(session)
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            event_type="quote_completed",
            payload=quote_payload.model_dump(),
        )
        if decision.intent == "recommend":
            session.preferences = self._ensure_recommendation_defaults(session, session.preferences)
            return self._respond_with_recommendations(
                session=session,
                request_id=request_id,
                user_text="用户上传了旧灯图片",
                decision=decision,
            )
        return ConversationResponse(
            session_id=session.session_id,
            state=session.stage,
            messages=[
                ConversationMessage(
                    role="assistant",
                    text=decision.reply,
                    suggestions=decision.suggestions,
                    cards=[CardEnvelope(type="recycle_quote", data=quote_payload.model_dump())],
                )
            ],
        )

    def handle_user_message(
        self,
        *,
        session_id: str,
        token: str,
        text: str,
        request_id: str,
    ) -> ConversationResponse:
        session = self.require_session(session_id=session_id, token=token)
        session.updated_at = utc_now()
        self._append_history(session, role="user", content=text)
        decision = self.llm_decide(
            session=session,
            user_text=text,
            request_id=request_id,
            interaction="chat_turn",
        )
        normalized_slots = self._normalize_llm_slots(decision.slots)
        if normalized_slots:
            session.preferences.update(normalized_slots)
            self.record_event(
                request_id=request_id,
                session_id=session.session_id,
                event_type="slot_extraction",
                payload={
                    "llm": decision.trace,
                    "slots": decision.slots,
                    "normalized_slots": normalized_slots,
                },
            )

        self._append_history(session, role="assistant", content=decision.reply)

        if not session.quote_payload:
            self.sessions.save(session)
            return ConversationResponse(
                session_id=session.session_id,
                state=session.stage,
                messages=[
                    ConversationMessage(
                        role="assistant",
                        text=decision.reply,
                        suggestions=decision.suggestions,
                    )
                ],
            )

        if decision.intent == "recommend":
            session.preferences = self._ensure_recommendation_defaults(session, session.preferences)
            return self._respond_with_recommendations(
                session=session,
                request_id=request_id,
                user_text=text,
                decision=decision,
            )

        if decision.intent == "checkout":
            self.sessions.save(session)
            if not session.selected_recommendation:
                return ConversationResponse(
                    session_id=session.session_id,
                    state=session.stage,
                    messages=[
                        ConversationMessage(
                            role="assistant",
                            text=decision.reply,
                            suggestions=decision.suggestions,
                        )
                    ],
                )
            return ConversationResponse(
                session_id=session.session_id,
                state=session.stage,
                    messages=[
                        ConversationMessage(
                            role="assistant",
                            text=decision.reply,
                            suggestions=decision.suggestions,
                            cards=[CardEnvelope(type="checkout_form", data={"session_id": session.session_id})],
                        )
                    ],
                )

        if self._missing_preferences(session.preferences):
            self.transition(session, Stage.COLLECTING_PREF)
        self.sessions.save(session)
        return ConversationResponse(
            session_id=session.session_id,
            state=session.stage,
            messages=[
                ConversationMessage(
                    role="assistant",
                    text=decision.reply,
                    suggestions=decision.suggestions,
                )
            ],
        )

    def submit_preferences(
        self,
        *,
        session_id: str,
        token: str,
        payload: dict[str, Any],
        request_id: str,
    ) -> ConversationResponse:
        session = self.require_session(session_id=session_id, token=token)
        if not session.quote_payload:
            raise ConflictError("old lamp quote is required before preferences")

        merged = dict(session.preferences)
        for key in ("install_type", "space", "budget_level"):
            value = str(payload.get(key) or "").strip()
            if value:
                merged[key] = value
        note = str(payload.get("note") or "").strip()
        if note:
            merged["note"] = note

        session.preferences = merged
        self._append_history(
            session,
            role="user",
            content=f"用户通过表单提交了偏好：{json.dumps(merged, ensure_ascii=False)}",
        )
        decision = self.llm_decide(
            session=session,
            user_text="用户通过表单提交了偏好，请继续对话。",
            request_id=request_id,
            interaction="preferences_submit",
        )
        normalized_slots = self._normalize_llm_slots(decision.slots)
        if normalized_slots:
            session.preferences.update(normalized_slots)
        session.preferences = self._ensure_recommendation_defaults(session, session.preferences)
        return self._respond_with_recommendations(
            session=session,
            request_id=request_id,
            user_text=note or "用户通过表单提交了偏好",
            decision=decision,
        )

    def select_recommendation(
        self,
        *,
        session_id: str,
        token: str,
        sku_id: str,
        request_id: str,
    ) -> RecommendationSelectResponse:
        session = self.require_session(session_id=session_id, token=token)
        payload = session.recommendation_payload or {}
        selected = next((item for item in payload.get("recommendations", []) if item.get("sku_id") == sku_id), None)
        if not selected:
            raise NotFoundError("selected recommendation not found")

        session.selected_recommendation = selected
        self.transition(session, Stage.CHECKOUT)
        session.updated_at = utc_now()
        self.sessions.save(session)
        draft = self.build_checkout_draft(session)
        response = RecommendationSelectResponse(
            session_id=session.session_id,
            selected=selected,
            draft=draft,
            next_action={
                "type": "checkout_form",
                "form_schema_url": f"/agent/forms/checkout?session_id={session.session_id}",
            },
        )
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            event_type="recommendation_selected",
            payload=response.model_dump(),
        )
        return response

    def get_checkout_form(
        self,
        *,
        session_id: str,
        token: str,
    ) -> CheckoutFormResponse:
        session = self.require_session(session_id=session_id, token=token)
        if not session.selected_recommendation:
            raise ConflictError("recommendation selection is required before checkout")

        draft = self.build_checkout_draft(session)
        payable_total = int(round(float(draft.selected_new_price) * 100 - float(draft.recycle_quote or 0.0) * 100))
        payable_total = max(payable_total, 100)
        return CheckoutFormResponse(
            session_id=session.session_id,
            form_schema=FORM_SCHEMA,
            defaults={
                "session_id": session.session_id,
                "trace_id": f"tr_{uuid.uuid4().hex[:10]}",
                "selected_old_sku": draft.selected_old_sku or "",
                "selected_new_sku": draft.selected_new_sku,
                "qty": str(draft.qty or 1),
                "payable_total": str(payable_total),
            },
            selection=draft,
            summary=CheckoutFormSummary(
                old_lamp=draft.selected_old_title or "",
                new_lamp=draft.selected_new_title,
                recycle_quote=float(draft.recycle_quote or 0.0),
                currency=draft.currency or "CNY",
                payable_total_fen=payable_total,
                todo="确认收货信息后即可生成支付二维码并继续下单流程。",
            ),
        )

    def normalize_address(self, payload: dict[str, Any]) -> AddressResponse:
        full_address = str(payload.get("full_address") or "").strip()
        if not full_address:
            full_address = " ".join(
                [
                    str(payload.get("region") or "").strip(),
                    str(payload.get("province") or "").strip(),
                    str(payload.get("city") or "").strip(),
                    str(payload.get("district") or "").strip(),
                    str(payload.get("street") or "").strip(),
                ]
            ).strip()
        if not full_address:
            raise ConflictError("address is required")

        province = str(payload.get("province") or "").strip()
        city = str(payload.get("city") or "").strip()
        district = str(payload.get("district") or "").strip()
        street = str(payload.get("street") or "").strip()
        completion_tips: list[str] = []
        if not province or not city:
            completion_tips.append("建议补充省市信息，便于物流和配送。")
        if not district:
            completion_tips.append("建议补充区县信息。")
        if not street:
            completion_tips.append("建议补充街道与门牌号。")

        return AddressResponse(
            full_address=full_address,
            region=str(payload.get("region") or "").strip(),
            province=province,
            city=city,
            district=district,
            street=street,
            postal_code=str(payload.get("postal_code") or "").strip(),
            longitude=float(payload.get("longitude") or 0.0),
            latitude=float(payload.get("latitude") or 0.0),
            location_source=str(payload.get("location_source") or "USER_INPUT").strip() or "USER_INPUT",
            address_source=str(payload.get("address_source") or "USER_INPUT").strip() or "USER_INPUT",
            validated=True,
            completion_tips=completion_tips,
        )

    def locate_address(self, payload: dict[str, Any]) -> AddressResponse:
        latitude = float(payload.get("latitude") or 0.0)
        longitude = float(payload.get("longitude") or 0.0)
        manual = str(payload.get("full_address") or "").strip()
        reverse = self._reverse_geocode(latitude=latitude, longitude=longitude)
        if reverse is None and manual:
            return AddressResponse(
                full_address=manual,
                region="",
                province="",
                city="",
                district="",
                street="",
                postal_code="",
                longitude=longitude,
                latitude=latitude,
                location_source="BROWSER_GEOLOCATION",
                address_source="BROWSER_GEOLOCATION",
                validated=True,
                completion_tips=["定位结果不完整，请手动补充详细地址。"],
            )
        if reverse is None:
            return AddressResponse(
                full_address=manual or f"当前位置({latitude:.5f}, {longitude:.5f})",
                region="",
                province="",
                city="",
                district="",
                street=manual or "请补充收货地址",
                postal_code="",
                longitude=longitude,
                latitude=latitude,
                location_source="BROWSER_GEOLOCATION",
                address_source="BROWSER_GEOLOCATION",
                validated=bool(latitude or longitude or manual),
                completion_tips=["已获取当前位置坐标，请补充详细收货地址。"],
            )
        return AddressResponse(
            full_address=manual or reverse.get("display_name", ""),
            region=reverse.get("region", ""),
            province=reverse.get("province", ""),
            city=reverse.get("city", ""),
            district=reverse.get("district", ""),
            street=reverse.get("street", ""),
            postal_code=reverse.get("postal_code", ""),
            longitude=longitude,
            latitude=latitude,
            location_source="OPENSTREETMAP_NOMINATIM",
            address_source="OPENSTREETMAP_NOMINATIM",
            validated=bool(manual or reverse.get("display_name")),
            completion_tips=([] if reverse.get("street") else ["定位成功，建议补充详细门牌号。"]),
        )

    def create_order(
        self,
        *,
        payload: CreateOrderRequest,
        token: str,
        request_id: str,
    ) -> OrderView:
        session = self.require_session(session_id=payload.session_id, token=token)
        if not session.selected_recommendation:
            raise ConflictError("recommendation selection is required before order creation")

        payable_total = max(int(payload.payable_total or 0), 100)
        order = OrderView(
            order_id=f"ord_{uuid.uuid4().hex[:12]}",
            trace_id=(payload.trace_id or f"tr_{uuid.uuid4().hex[:10]}"),
            user_id=payload.user.user_id,
            contact_name=payload.user.name,
            contact_phone=payload.user.phone,
            address_region=payload.address.region,
            full_address=payload.address.full_address,
            receiver_longitude=payload.address.longitude,
            receiver_latitude=payload.address.latitude,
            location_source=payload.address.location_source or "USER_INPUT",
            address_source=payload.address.address_source or "USER_INPUT",
            access_domain=payload.access_domain,
            status="CREATED",
            order_status="CREATED",
            payment_status="UNPAID",
            pay_status="UNPAID",
            payable_total=payable_total,
            amount_currency=payload.currency,
            amount_unit=payload.amount_unit,
            snapshot=payload.model_dump(),
            mock_mode=self.settings.payment_mode == "mock",
            payment_mode=self.settings.payment_mode,
            requires_review=session.requires_review,
        )
        order.snapshot["session_id"] = session.session_id
        order.snapshot["created_at"] = iso_now()
        order.recycle_progress = self._build_recycle_progress(order)
        order.shipment_progress = self._build_shipment_progress(order)
        saved = self.orders.upsert(order)
        session.order_id = saved.order_id
        session.updated_at = utc_now()
        self.sessions.save(session)
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            order_id=saved.order_id,
            event_type="order_created",
            payload=saved.model_dump(),
        )
        return saved

    def create_qr(
        self,
        *,
        order_id: str,
        payload: CreateQrRequest,
        app_origin: str,
        request_id: str,
    ) -> CreateQrResponse:
        order = self.get_order(order_id=order_id, sync=False)

        expires_at = utc_now() + timedelta(minutes=10)
        qr_token = uuid.uuid4().hex
        code_url = f"{app_origin}/order/{order.order_id}/electronic?qrToken={qr_token}"
        order.qr_token = qr_token
        order.qr_status = "READY"
        order.qr_expires_at = expires_at.isoformat().replace("+00:00", "Z")
        order.payment_trade_type = payload.trade_type
        order.payment_idempotent_key = payload.idempotent_key or f"prepay:{uuid.uuid4().hex[:8]}"
        order.payment_code_url = code_url
        order.payment_h5_url = code_url
        order.payment_updated_at = iso_now()
        order.prepay_id = f"prepay_{uuid.uuid4().hex[:10]}"
        order.recycle_progress = self._build_recycle_progress(order)
        saved = self.orders.upsert(order)
        response = CreateQrResponse(
            order_id=saved.order_id,
            trace_id=saved.trace_id,
            qr_token=qr_token,
            code_url=code_url,
            h5_url=code_url,
            expire_at=saved.qr_expires_at or order.qr_expires_at or "",
            payable_total=saved.payable_total,
            currency=saved.amount_currency,
            amount_unit=saved.amount_unit,
            trade_type=payload.trade_type,
            mock_mode=saved.mock_mode,
        )
        self.record_event(
            request_id=request_id,
            session_id=saved.snapshot.get("session_id"),
            order_id=saved.order_id,
            event_type="payment_qr_created",
            payload=response.model_dump(),
        )
        return response

    def get_order(self, *, order_id: str, sync: bool = True) -> OrderView:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError("order not found")
        if sync:
            order = self.sync_order(order)
        return order

    def get_electronic_order(self, *, order_id: str, qr_token: str) -> ElectronicOrderResponse:
        order = self.get_order(order_id=order_id, sync=True)
        if not order.qr_token or order.qr_token != qr_token:
            raise UnauthorizedError("qr token not found")
        items = order.snapshot.get("items") or []
        total_qty = sum(int(item.get("qty") or 1) for item in items) or 1
        unit_price = round(order.payable_total / 100 / total_qty, 2)
        timeline = [
            {"time": order.snapshot.get("created_at") or iso_now(), "event": "订单已创建"},
            {"time": order.payment_updated_at or order.snapshot.get("created_at") or iso_now(), "event": f"支付状态：{order.payment_status}"},
            {"time": order.paid_at or order.payment_updated_at or order.snapshot.get("created_at") or iso_now(), "event": f"履约状态：{order.order_status}"},
        ]
        return ElectronicOrderResponse(
            order_id=order.order_id,
            trace_id=order.trace_id,
            code="SUCCESS",
            status_code=200,
            order_basic={
                "order_id": order.order_id,
                "status": order.order_status,
                "created_at": order.snapshot.get("created_at") or iso_now(),
            },
            items=[
                {
                    "sku": item.get("selected_new_sku") or item.get("selected_old_sku") or "",
                    "name": item.get("selected_new_title") or item.get("selected_old_title") or "灯具",
                    "qty": int(item.get("qty") or 1),
                    "price": unit_price,
                }
                for item in items
            ],
            payment={
                "total": round(order.payable_total / 100, 2),
                "pay_status": order.payment_status,
                "paid_at": order.paid_at or "",
            },
            waybill={"waybill_id": order.waybill_id or "", "status": order.waybill_status or ""},
            timeline=timeline,
        )

    def get_logistics(self, *, order_id: str) -> LogisticsResponse:
        order = self.get_order(order_id=order_id, sync=True)
        destination_lng = float(order.receiver_longitude or 121.544)
        destination_lat = float(order.receiver_latitude or 31.221)
        nodes = [
            {"lng": 121.4737, "lat": 31.2304, "label": "回收中心", "status": "created"},
            {"lng": 121.5, "lat": 31.24, "label": "中转仓", "status": "in_transit"},
            {"lng": destination_lng, "lat": destination_lat, "label": "收货地址", "status": order.waybill_status or "pending"},
        ]
        events = [
            {"time": order.snapshot.get("created_at") or iso_now(), "event": "订单创建", "status": "CREATED"},
            {"time": order.payment_updated_at or order.snapshot.get("created_at") or iso_now(), "event": "支付状态同步", "status": order.payment_status},
            {"time": order.paid_at or order.payment_updated_at or order.snapshot.get("created_at") or iso_now(), "event": "履约状态同步", "status": order.order_status},
        ]
        return LogisticsResponse(
            order_id=order.order_id,
            waybill_id=order.waybill_id or "",
            status=order.waybill_status or order.order_status,
            trace_id=order.trace_id,
            provider="workflow-simulator",
            events=events,
            nodes=nodes,
        )

    def get_logistics_map(self, *, order_id: str) -> LogisticsMapResponse:
        logistics = self.get_logistics(order_id=order_id)
        return LogisticsMapResponse(
            order_id=logistics.order_id,
            waybill_id=logistics.waybill_id,
            provider=logistics.provider,
            nodes=logistics.nodes,
            route=[[float(node["lng"]), float(node["lat"])] for node in logistics.nodes],
        )

    def quote_image(self, *, image_path: Path, request_id: str) -> QuoteResponse:
        ready, reason = self.preflight_quote()
        if not ready:
            if not self.settings.allow_review_fallback:
                raise ServiceUnavailable("model not ready", details={"reason": reason})
            payload = self.build_review_quote(image_path=image_path, review_reasons=[reason])
            self.record_event(request_id=request_id, event_type="quote_review_fallback", payload=payload.model_dump())
            return payload

        try:
            from image_quote_system.pipeline import quote_single_image

            result = quote_single_image(image_path, config_dir=self.settings.config_dir, topk=3)
            payload = self.build_quote_payload(result)
        except Exception as exc:  # pragma: no cover - depends on optional runtime stack
            if not self.settings.allow_review_fallback:
                raise ServiceUnavailable("model not ready", details={"reason": str(exc)}) from exc
            payload = self.build_review_quote(image_path=image_path, review_reasons=[f"quote_exception:{type(exc).__name__}"])
            self.record_event(request_id=request_id, event_type="quote_review_fallback", payload=payload.model_dump())
            return payload

        review_reasons: list[str] = []
        detection_summary = payload.quote.get("detection_summary") or {}
        if detection_summary.get("used_fallback"):
            review_reasons.append("detection_fallback_used")
        if "fallback" in str(payload.quote.get("retrieval_backend") or "").lower():
            review_reasons.append("retrieval_fallback_used")
        if review_reasons:
            if not self.settings.allow_review_fallback:
                raise ServiceUnavailable("model not ready", details={"reasons": review_reasons})
            payload.summary.requires_review = True
            payload.summary.review_reasons = review_reasons
            payload.summary.checkout_allowed = False
        return payload

    def recommend(
        self,
        *,
        reference_sku_id: str,
        preferences: dict[str, str] | None,
        session_id: str | None = None,
        requires_review: bool = False,
    ) -> RecommendationResponse:
        ready, reason = self.preflight_recommendation()
        if not ready:
            raise ServiceUnavailable("model not ready", details={"reason": reason})
        from image_quote_system.recommendation import recommend_replacement_lamps

        result = recommend_replacement_lamps(
            reference_sku_id=reference_sku_id,
            preferences=preferences or {},
            config_dir=self.settings.config_dir,
            limit=3,
        )
        payload = RecommendationResponse.model_validate(
            {
                **result,
                "session_id": session_id,
                "space": (preferences or {}).get("space"),
                "selection_api": (
                    {"path": f"/agent/sessions/{session_id}/recommendations/select", "method": "POST"} if session_id else None
                ),
                "source": "catalog",
                "requires_review": requires_review,
                "review_reasons": ["quote_requires_review"] if requires_review else [],
                "checkout_allowed": not requires_review,
            }
        )
        catalog_rows = self.load_catalog_rows()
        for item in payload.recommendations:
            if item.image_path and self._is_catalog_path(item.image_path):
                continue
            item.image_path = self._pick_catalog_image(item.sku_id, catalog_rows)
            item.image_missing = item.image_path is None
        return payload

    def preflight_quote(self) -> tuple[bool, str]:
        if self.settings.workflow_mode == "mock":
            return False, "workflow mode mock"
        try:
            import open_clip  # type: ignore  # noqa: F401
        except Exception as exc:
            return False, f"dependency_missing:{type(exc).__name__}"
        return True, "ready"

    def preflight_classifier(self) -> tuple[bool, str]:
        if self.settings.workflow_mode == "mock":
            return False, "workflow mode mock"
        try:
            from transformers import pipeline  # noqa: F401
        except Exception as exc:
            return False, f"dependency_missing:{type(exc).__name__}"
        return True, "ready"

    def preflight_recommendation(self) -> tuple[bool, str]:
        try:
            rows = self.load_catalog_rows()
        except Exception as exc:  # pragma: no cover - filesystem issue
            return False, f"catalog_load_failed:{type(exc).__name__}"
        return (bool(rows), "ready" if rows else "catalog_empty")

    def preflight_payment(self) -> tuple[bool, str]:
        if self.settings.payment_mode == "real":
            return False, "real payment provider not configured"
        return True, "mock mode"

    def require_session(self, *, session_id: str, token: str) -> SessionState:
        payload = self.tokens.verify(token)
        if payload.session_id != session_id:
            raise UnauthorizedError("session token does not match session")
        session = self.sessions.load(session_id)
        if session is None:
            raise NotFoundError("session not found")
        if session.user_id != payload.user_id:
            raise UnauthorizedError("session user mismatch")
        return session

    def transition(self, session: SessionState, next_stage: Stage) -> None:
        if session.stage == next_stage:
            return
        allowed = TRANSITIONS.get(session.stage, [])
        if next_stage not in allowed:
            raise ConflictError(f"invalid stage transition: {session.stage} -> {next_stage}")
        session.stage = next_stage

    def store_upload(self, *, raw: bytes, filename: str, content_type: str) -> tuple[Path, UploadInfo]:
        if len(raw) > self.settings.max_upload_bytes:
            raise ConflictError("file too large")
        if content_type and content_type not in self.settings.allowed_mime_types:
            raise ConflictError("unsupported mime type")
        try:
            image = Image.open(io.BytesIO(raw))
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ConflictError("invalid image upload") from exc

        suffix = Path(filename).suffix.lower() or ".png"
        upload_path = (self.settings.upload_dir / f"{uuid.uuid4().hex}{suffix}").resolve()
        upload_path.write_bytes(raw)
        self._ensure_within_base(upload_path)
        upload = UploadInfo(
            filename=Path(filename).name or upload_path.name,
            stored_path=str(upload_path.relative_to(self.settings.base_dir).as_posix()),
            size_bytes=len(raw),
        )
        return upload_path, upload

    def resolve_image_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = self.settings.base_dir / candidate
        resolved = candidate.resolve()
        self._ensure_within_base(resolved)
        return resolved

    def record_event(
        self,
        *,
        request_id: str,
        event_type: str,
        payload: dict[str, Any],
        session_id: str | None = None,
        order_id: str | None = None,
    ) -> None:
        event = {
            "request_id": request_id,
            "session_id": session_id,
            "order_id": order_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": iso_now(),
        }
        self.events.record(
            request_id=request_id,
            session_id=session_id,
            order_id=order_id,
            event_type=event_type,
            payload=payload,
        )
        log_path = self.settings.log_dir / "agent-events.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def build_quote_payload(self, result: Any) -> QuoteResponse:
        payload = result.to_dict()
        first = payload["line_items"][0] if payload.get("line_items") else None
        return QuoteResponse(
            quote=payload,
            summary=QuoteSummary(
                recognized_type=first["matched_product"]["metadata"].get("visual_style", "") if first else "",
                matched_sku_id=first["matched_sku_id"] if first else "",
                matched_title=first["title"] if first else "",
                recycle_quote=float(payload.get("total_quote", 0.0)),
                currency=str(payload.get("currency", "CNY")),
                detection_backend=str(payload.get("detection_backend", "")),
                checkout_allowed=True,
            ),
            follow_up_questions=list(FOLLOW_UP_QUESTIONS),
        )

    def build_review_quote(self, *, image_path: Path, review_reasons: list[str]) -> QuoteResponse:
        catalog = self.load_catalog_rows()
        anchor = catalog[0] if catalog else {
            "sku_id": "",
            "title": "Manual Review Required",
            "visual_style": "any",
            "base_price": 0,
        }
        recycle_quote = round(float(anchor.get("base_price", 0.0)) * 0.28, 2)
        payload = {
            "image_path": str(image_path),
            "detection_backend": "review-fallback",
            "embedding_backend": "review-fallback",
            "retrieval_backend": "catalog-rules",
            "currency": "CNY",
            "total_quote": recycle_quote,
            "price_summary": {
                "line_item_count": 1,
                "subtotal_before_residual": recycle_quote,
                "residual_total": 0.0,
                "total_quote": recycle_quote,
                "currency": "CNY",
            },
            "detection_summary": {
                "backend": "review-fallback",
                "used_fallback": True,
                "notes": review_reasons,
                "detections": [],
            },
            "line_items": [
                {
                    "detection_index": 0,
                    "matched_sku_id": anchor.get("sku_id", ""),
                    "title": anchor.get("title", ""),
                    "base_price": float(anchor.get("base_price", 0.0)),
                    "final_quote": recycle_quote,
                    "similarity_score": 0.0,
                    "detection_confidence": 0.0,
                    "matched_product": {"metadata": {"visual_style": anchor.get("visual_style", "any")}},
                    "topk_similar_items": [],
                    "breakdown": {"requires_review": True},
                    "price_composition": {"requires_review": True},
                }
            ],
        }
        return QuoteResponse(
            quote=payload,
            summary=QuoteSummary(
                recognized_type=str(anchor.get("visual_style", "any")),
                matched_sku_id=str(anchor.get("sku_id", "")),
                matched_title=str(anchor.get("title", "")),
                recycle_quote=recycle_quote,
                currency="CNY",
                detection_backend="review-fallback",
                requires_review=True,
                review_reasons=review_reasons,
                checkout_allowed=False,
            ),
            follow_up_questions=list(FOLLOW_UP_QUESTIONS),
        )

    def build_checkout_draft(self, session: SessionState) -> CheckoutDraft:
        quote = session.quote_payload or {}
        summary = quote.get("summary") or {}
        selection = session.selected_recommendation or {}
        upload = quote.get("upload") or {}
        return CheckoutDraft(
            selected_old_sku=summary.get("matched_sku_id"),
            selected_old_title=summary.get("matched_title"),
            selected_old_image_path=upload.get("stored_path"),
            selected_old_kind=summary.get("recognized_type"),
            selected_new_sku=str(selection.get("sku_id", "")),
            selected_new_title=str(selection.get("title", "")),
            selected_new_image_path=selection.get("image_path"),
            selected_new_kind=selection.get("visual_style"),
            selected_new_price=float(selection.get("base_price") or 0.0),
            recycle_quote=float(summary.get("recycle_quote") or 0.0),
            currency=str(summary.get("currency") or "CNY"),
            qty=1,
        )

    def load_catalog_rows(self) -> list[dict[str, Any]]:
        if self._catalog_cache is not None:
            return self._catalog_cache
        config = load_config(self.settings.config_dir)
        catalog_path = self.settings.base_dir / config["paths"]["catalog_csv"]
        self._catalog_cache = load_catalog(catalog_path)
        return self._catalog_cache

    def sync_order(self, order: OrderView) -> OrderView:
        changed = False
        now = utc_now()
        payment_updated_at = parse_iso(order.payment_updated_at)
        paid_at = parse_iso(order.paid_at)
        if order.mock_mode and order.qr_status == "READY" and payment_updated_at and now - payment_updated_at >= timedelta(seconds=6):
            order.payment_status = "PAID"
            order.pay_status = "PAID"
            order.order_status = "PAID"
            order.status = "PAID"
            order.paid_at = order.paid_at or iso_now()
            order.paid_amount_total = order.payable_total
            order.transaction_id = order.transaction_id or f"mock_tx_{uuid.uuid4().hex[:10]}"
            order.qr_status = "SCANNED"
            order.waybill_id = order.waybill_id or f"wb_{uuid.uuid4().hex[:10]}"
            order.waybill_status = order.waybill_status or "CREATED"
            changed = True
            paid_at = parse_iso(order.paid_at)
        if paid_at and now - paid_at >= timedelta(seconds=3) and order.order_status == "PAID":
            order.order_status = "FULFILLING"
            order.status = "FULFILLING"
            order.waybill_status = "PICKED_UP"
            changed = True
        if paid_at and now - paid_at >= timedelta(seconds=7) and order.order_status == "FULFILLING":
            order.order_status = "IN_TRANSIT"
            order.status = "IN_TRANSIT"
            order.waybill_status = "IN_TRANSIT"
            changed = True
        if paid_at and now - paid_at >= timedelta(seconds=12) and order.order_status == "IN_TRANSIT":
            order.order_status = "DELIVERING"
            order.status = "DELIVERING"
            order.waybill_status = "OUT_FOR_DELIVERY"
            changed = True
        if changed:
            order.recycle_progress = self._build_recycle_progress(order)
            order.shipment_progress = self._build_shipment_progress(order)
            order.payment_updated_at = order.payment_updated_at or iso_now()
            order = self.orders.upsert(order)
        return order

    def _respond_with_recommendations(
        self,
        *,
        session: SessionState,
        request_id: str,
        user_text: str,
        decision: LLMDecision,
    ) -> ConversationResponse:
        quote_summary = (session.quote_payload or {}).get("summary") or {}
        payload = self.recommend(
            reference_sku_id=str(quote_summary.get("matched_sku_id") or ""),
            preferences=session.preferences,
            session_id=session.session_id,
            requires_review=session.requires_review,
        )
        ecommerce_query = self._build_ecommerce_query(session=session, decision=decision, user_text=user_text)
        self._enrich_recommendations_with_buy_links(payload, ecommerce_query)
        session.recommendation_payload = payload.model_dump()
        self.transition(session, Stage.RECOMMENDING)
        session.updated_at = utc_now()
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            event_type="route_decision",
            payload={
                "llm": decision.trace,
                "intent": decision.intent,
                "confidence": decision.confidence,
                "slots": decision.slots,
                "user_text": user_text,
            },
        )
        self.record_event(
            request_id=request_id,
            session_id=session.session_id,
            event_type="recommendation_built",
            payload={
                "source": "catalog",
                "requires_review": session.requires_review,
                "review_reasons": session.review_reasons,
                "recommendations": payload.model_dump(),
            },
        )
        self._append_history(session, role="assistant", content=decision.reply)
        self.sessions.save(session)
        return ConversationResponse(
            session_id=session.session_id,
            state=session.stage,
            messages=[
                ConversationMessage(
                    role="assistant",
                    text=decision.reply,
                    suggestions=decision.suggestions,
                    cards=[CardEnvelope(type="replacement_recommendations", data=payload.model_dump())],
                )
            ],
        )

    def _build_ecommerce_query(self, *, session: SessionState, decision: LLMDecision, user_text: str) -> str:
        parts: list[str] = []
        room = str(decision.slots.get("room") or session.preferences.get("space") or "").strip()
        install_type = str(decision.slots.get("install_type") or session.preferences.get("install_type") or "").strip()
        material = str(decision.slots.get("material") or session.preferences.get("material") or "").strip()
        budget_level = str(decision.slots.get("budget_level") or session.preferences.get("budget_level") or "").strip()
        budget = str(decision.slots.get("budget") or "").strip()

        for value in (room, install_type, material, budget_level, budget):
            if value:
                parts.append(value)
        if not parts:
            parts.append(user_text)
        return " ".join(parts)

    def _enrich_recommendations_with_buy_links(self, payload: RecommendationResponse, query: str) -> None:
        external_products = self.ecommerce.search_products(query, limit=max(len(payload.recommendations), 1))
        for index, item in enumerate(payload.recommendations):
            external = external_products[index] if index < len(external_products) else None
            item.buy_url = (
                str((external or {}).get("buy_url", "")).strip()
                or build_taobao_search_url(item.title or query)
            )
            item.buy_platform = str((external or {}).get("platform", "")).strip() or "taobao-search"
            item.internal_checkout = True

    def _build_pre_upload_reply(self, *, text: str, preferences: dict[str, str]) -> dict[str, Any]:
        normalized = str(text or "").strip().lower()
        pref_text = self._describe_preferences(preferences)
        greeting = any(keyword in normalized for keyword in ("你好", "嗨", "hello", "hi", "在吗"))
        capability = any(keyword in normalized for keyword in ("能做什么", "怎么用", "帮助", "功能", "流程"))
        recommendation = any(keyword in normalized for keyword in ("推荐", "换新", "预算", "客厅", "卧室", "吊灯", "壁灯", "落地灯"))

        if greeting and pref_text:
            return {
                "text": f"你好，我先记住你刚才提到的需求了：{pref_text}。你接下来发一张旧灯照片，我就能继续做识别、估价和换新推荐。",
                "suggestions": ["上传旧灯照片", "我想补充预算", "我想补充安装空间"],
            }
        if greeting:
            return {
                "text": "你好，我是灯具换新助手。你可以先跟我说空间、预算、想换成什么类型，也可以直接上传旧灯照片，我会继续帮你做识别、估价和推荐。",
                "suggestions": ["上传旧灯照片", "我想先说预算和空间", "你能帮我做什么"],
            }
        if capability:
            return {
                "text": "我可以帮你走完整个换新对话：先识别旧灯、给回收估价，再按你的空间和预算推荐新灯，最后把结果带进下单流程。",
                "suggestions": ["上传旧灯照片", "客厅吊灯，预算1000", "先告诉你我的需求"],
            }
        if recommendation and pref_text:
            return {
                "text": f"可以，我先把你的偏好记下来了：{pref_text}。为了让推荐更靠谱，再发一张旧灯照片，我会把旧灯识别结果和这些偏好一起考虑进去。",
                "suggestions": ["上传旧灯照片", "再补充一点预算", "再补充安装空间"],
            }
        if recommendation:
            return {
                "text": "可以先聊需求。我建议你先告诉我安装空间、预算和想换的灯具类型；如果再补一张旧灯照片，我就能把估价和推荐一起做出来。",
                "suggestions": ["客厅吊灯，预算1000", "卧室壁灯，预算500", "上传旧灯照片"],
            }
        if pref_text:
            return {
                "text": f"我先记住了：{pref_text}。下一步你发一张旧灯照片，我会继续做识别和报价，然后按这些条件给你推荐。",
                "suggestions": ["上传旧灯照片", "我还想补充需求"],
            }
        return {
            "text": "我可以先和你一起把需求聊清楚，也可以直接从图片开始。你发旧灯照片，我会继续识别；你先说预算和空间，我也会帮你记住。",
            "suggestions": ["上传旧灯照片", "客厅吊灯，预算1000", "你能帮我做什么"],
        }

    def _build_collect_preferences_reply(self, preferences: dict[str, str]) -> dict[str, Any]:
        missing = self._missing_preferences(preferences)
        pref_text = self._describe_preferences(preferences)
        if not missing:
            return {
                "text": f"收到，我已经把需求整理好了：{pref_text}。我这就按这些条件给你筛目录推荐。",
                "suggestions": ["开始推荐", "我想改一下预算"],
            }
        missing_text = "、".join(missing)
        if pref_text:
            return {
                "text": f"我先记住了：{pref_text}。为了继续往下推荐，还差 {missing_text}。",
                "suggestions": self._suggestions_for_missing(missing),
            }
        return {
            "text": f"我还需要补齐几个关键信息，才能把推荐做得更像真人顾问：{missing_text}。",
            "suggestions": self._suggestions_for_missing(missing),
        }

    def _build_recommendation_reply(
        self,
        *,
        session: SessionState,
        payload: RecommendationResponse,
        user_text: str,
    ) -> dict[str, Any]:
        pref_text = self._describe_preferences(session.preferences)
        count = len(payload.recommendations)
        if session.requires_review:
            return {
                "text": (
                    f"我先按 {pref_text or '当前偏好'} 给你筛了 {count} 个目录候选。"
                    "不过旧灯识别结果还在人工复核里，所以我先只给你看推荐，不开放下单。"
                ),
                "suggestions": ["看看第一个推荐", "我想改预算", "重新上传一张更清晰的旧灯图"],
            }
        return {
            "text": f"我已经结合 {pref_text or '你的需求'} 给你筛了 {count} 个推荐。你先看卡片，如果想要更便宜、更新潮或更适合客厅，我可以继续帮你缩小范围。",
            "suggestions": ["更便宜一点", "更适合客厅", "帮我下单"],
        }

    def _build_upload_reply(self, session: SessionState, quote_payload: QuoteResponse) -> str:
        pref_text = self._describe_preferences(session.preferences)
        if quote_payload.summary.requires_review:
            if pref_text:
                return (
                    f"我先看完这张旧灯图了，但这次识别结果我拿不准，不想误导你，所以先标记为人工复核。"
                    f"你前面提到的需求我还记着：{pref_text}。我可以先继续给你看目录推荐，但不会直接进入下单。"
                )
            return (
                "我先看完这张旧灯图了，但这次识别结果我拿不准，不想误导你，所以先标记为人工复核。"
                "你可以继续补充空间、预算和类型，我先给你看目录推荐，但不会直接进入下单。"
            )
        if pref_text:
            return f"旧灯我先帮你识别好了，我也记着你前面说的需求：{pref_text}。如果还有没补完的偏好，我们继续补一下，我就开始给你筛推荐。"
        return "旧灯我先帮你识别好了。接下来你告诉我安装空间、预算和想换的灯具类型，我就继续给你筛推荐。"

    def _suggestions_before_quote(self, session: SessionState, decision: LLMDecision) -> list[str]:
        if decision.intent == "recommend":
            return ["上传旧灯照片", "我再补充一点预算", "我再说一下安装空间"]
        if session.preferences:
            return ["上传旧灯照片", "我还想补充需求", "你能帮我做什么"]
        return ["上传旧灯照片", "客厅吊灯，预算1000", "你能帮我做什么"]

    def _suggestions_after_quote(self, session: SessionState) -> list[str]:
        if session.requires_review:
            return ["重新上传更清晰的旧灯图", "继续补充预算", "先看目录推荐"]
        missing = self._missing_preferences(session.preferences)
        if missing:
            return self._suggestions_for_missing(missing)
        return ["查看推荐", "我想改预算", "帮我下单"]

    def _suggestions_after_recommendation(self, session: SessionState) -> list[str]:
        if session.requires_review:
            return ["看看第一个推荐", "我想改预算", "重新上传一张更清晰的旧灯图"]
        return ["更便宜一点", "更适合客厅", "帮我下单"]

    def _describe_preferences(self, preferences: dict[str, str]) -> str:
        parts: list[str] = []
        if preferences.get("space"):
            parts.append(self._space_label(preferences["space"]))
        if preferences.get("budget_level"):
            parts.append(self._budget_label(preferences["budget_level"]))
        if preferences.get("install_type"):
            parts.append(self._install_type_label(preferences["install_type"]))
        if preferences.get("note"):
            parts.append(f"备注：{preferences['note']}")
        return " / ".join(part for part in parts if part)

    def _suggestions_for_missing(self, missing: list[str]) -> list[str]:
        suggestions: list[str] = []
        if "安装空间" in missing:
            suggestions.append("装在客厅")
        if "预算范围" in missing:
            suggestions.append("预算1000左右")
        if "偏好类型" in missing:
            suggestions.append("我想换吊灯")
        return suggestions or ["继续补充需求"]

    def _space_label(self, value: str) -> str:
        return {
            "living_room": "客厅",
            "bedroom": "卧室",
            "dining_room": "餐厅",
            "office": "办公室",
            "store": "门店",
        }.get(value, value)

    def _budget_label(self, value: str) -> str:
        return {
            "economy": "预算偏经济",
            "balanced": "预算均衡",
            "premium": "预算偏高端",
        }.get(value, value)

    def _install_type_label(self, value: str) -> str:
        return {
            "pendant": "吊灯",
            "wall": "壁灯",
            "floor": "落地灯",
            "any": "类型都可以",
        }.get(value, value)

    def _ensure_recommendation_defaults(
        self,
        session: SessionState,
        merged_preferences: dict[str, str],
    ) -> dict[str, str]:
        output = dict(merged_preferences)
        summary = (session.quote_payload or {}).get("summary") or {}
        output.setdefault("install_type", str(summary.get("recognized_type") or "any") or "any")
        output.setdefault("budget_level", "balanced")
        output.setdefault("space", "living_room")
        return output

    def _missing_preferences(self, preferences: dict[str, str]) -> list[str]:
        labels = [("space", "安装空间"), ("budget_level", "预算范围"), ("install_type", "偏好类型")]
        return [label for key, label in labels if not preferences.get(key)]

    def _build_collect_preferences_fallback(self, preferences: dict[str, str]) -> str:
        missing = self._missing_preferences(preferences)
        if not missing:
            return "我已经理解你的偏好，可以开始给你推荐目录灯具。"
        return "为了生成更准确的推荐，请继续补充：" + "、".join(missing) + "。"

    def _build_recycle_progress(self, order: OrderView) -> list[dict[str, Any]]:
        return [
            {"key": "created", "label": "订单创建", "done": True},
            {"key": "qr_ready", "label": "支付二维码生成", "done": order.qr_status == "READY" or order.qr_status == "SCANNED"},
            {"key": "paid", "label": "支付完成", "done": order.payment_status == "PAID"},
        ]

    def _build_shipment_progress(self, order: OrderView) -> list[dict[str, Any]]:
        current = order.order_status
        states = ["CREATED", "FULFILLING", "IN_TRANSIT", "DELIVERING"]
        index = states.index(current) if current in states else 0
        labels = [
            ("created", "履约受理"),
            ("fulfilling", "上门回收"),
            ("in_transit", "运输中"),
            ("delivering", "派送中"),
        ]
        return [{"key": key, "label": label, "done": idx <= index} for idx, (key, label) in enumerate(labels)]

    def _reverse_geocode(self, *, latitude: float, longitude: float) -> dict[str, str] | None:
        if abs(latitude) < 1e-9 and abs(longitude) < 1e-9:
            return None
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?format=jsonv2&lat={latitude:.8f}&lon={longitude:.8f}"
            "&addressdetails=1&accept-language=zh-CN"
        )
        request = urllib_request.Request(
            url,
            headers={
                "User-Agent": "ai-light-workflow/2.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(request, timeout=8) as response:  # noqa: S310
                raw = response.read()
        except (urllib_error.URLError, TimeoutError):
            return None
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        address = payload.get("address")
        if not isinstance(address, dict):
            return None

        def pick(*keys: str) -> str:
            for key in keys:
                value = str(address.get(key, "")).strip()
                if value:
                    return value
            return ""

        road = pick("road", "street", "pedestrian")
        house_number = pick("house_number")
        return {
            "region": str(address.get("country_code", "")).upper(),
            "province": pick("state", "province", "region"),
            "city": pick("city", "town", "municipality", "county", "village"),
            "district": pick("city_district", "district", "county", "suburb"),
            "street": " ".join(part for part in (road, house_number) if part).strip(),
            "postal_code": pick("postcode"),
            "display_name": str(payload.get("display_name", "")).strip(),
        }

    def _get_classifier(self) -> OpenSourceLampTypeClassifier:
        if self._classifier is None:
            self._classifier = OpenSourceLampTypeClassifier()
        return self._classifier

    def _ensure_within_base(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self.settings.base_dir)
        except ValueError as exc:
            raise ConflictError("path is outside base dir") from exc

    def _is_catalog_path(self, raw_path: str) -> bool:
        normalized = raw_path.replace("\\", "/")
        return normalized.startswith("data/") or normalized.startswith("data\\")

    def _pick_catalog_image(self, sku_id: str, rows: list[dict[str, Any]]) -> str | None:
        if not rows:
            return None
        exact = next((row for row in rows if str(row.get("sku_id", "")).strip() == sku_id), None)
        if exact and str(exact.get("image_path", "")).strip():
            return str(exact.get("image_path", "")).strip()
        ordered = [
            str(row.get("image_path", "")).strip()
            for row in rows
            if str(row.get("image_path", "")).strip()
        ]
        if not ordered:
            return None
        index = abs(hash(sku_id or "lamp")) % len(ordered)
        return ordered[index]
