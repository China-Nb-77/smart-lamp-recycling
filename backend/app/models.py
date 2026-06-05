from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Stage(str, Enum):
    INIT = "init"
    QUOTE_DONE = "quote_done"
    COLLECTING_PREF = "collecting_pref"
    RECOMMENDING = "recommending"
    CHECKOUT = "checkout"


TRANSITIONS = {
    Stage.INIT: [Stage.QUOTE_DONE],
    Stage.QUOTE_DONE: [Stage.COLLECTING_PREF, Stage.RECOMMENDING],
    Stage.COLLECTING_PREF: [Stage.RECOMMENDING],
    Stage.RECOMMENDING: [Stage.CHECKOUT],
    Stage.CHECKOUT: [],
}


class CardEnvelope(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class ConversationMessage(BaseModel):
    role: Literal["assistant", "user", "system"]
    text: str = ""
    suggestions: list[str] = Field(default_factory=list)
    cards: list[CardEnvelope] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    session_id: str
    state: Stage
    messages: list[ConversationMessage] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    user_id: str | None = None
    client_session_id: str | None = None


class SessionCreateResponse(ConversationResponse):
    session_token: str
    user_id: str
    expires_at: datetime


class UserMessageRequest(BaseModel):
    text: str


class QuotePathRequest(BaseModel):
    image_path: str
    topk: int | None = None


class RecommendRequest(BaseModel):
    reference_sku_id: str
    preferences: dict[str, str] | None = None
    limit: int = 3


class ClassifyPathRequest(BaseModel):
    image_path: str
    candidate_labels: list[str] | None = None
    topk: int = 3


class FollowUpOption(BaseModel):
    value: str
    label: str


class FollowUpQuestion(BaseModel):
    id: Literal["install_type", "budget_level", "space"]
    question: str
    options: list[FollowUpOption]


class UploadInfo(BaseModel):
    filename: str
    stored_path: str
    size_bytes: int


class QuoteSummary(BaseModel):
    recognized_type: str = ""
    matched_sku_id: str = ""
    matched_title: str = ""
    recycle_quote: float = 0.0
    currency: str = "CNY"
    detection_backend: str = ""
    explanation: str | None = None
    lamp_type_label: str | None = None
    lamp_type_score: float | None = None
    lamp_type_backend: str | None = None
    lamp_type_model_id: str | None = None
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    checkout_allowed: bool = True


class QuoteResponse(BaseModel):
    quote: dict[str, Any]
    summary: QuoteSummary
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    upload: UploadInfo | None = None


class PreferencesPayload(BaseModel):
    install_type: str = "any"
    budget_level: str = "balanced"
    material: str = "any"
    space: str | None = None


class RecommendationItem(BaseModel):
    sku_id: str
    title: str
    image_path: str | None = None
    image_missing: bool | None = None
    buy_url: str | None = None
    buy_platform: str | None = None
    internal_checkout: bool = True
    visual_style: str
    material: str
    size_band: str = ""
    craft: str = ""
    base_price: float
    fit_score: float
    recommendation_reasons: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    session_id: str | None = None
    reference: dict[str, Any]
    preferences: PreferencesPayload
    space: str | None = None
    selection_api: dict[str, str] | None = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    source: str = "catalog"
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    checkout_allowed: bool = True


class PreferenceSubmitRequest(BaseModel):
    install_type: str | None = None
    space: str | None = None
    budget_level: str | None = None
    note: str | None = None


class RecommendationSelectRequest(BaseModel):
    sku_id: str


class CheckoutDraft(BaseModel):
    selected_old_sku: str | None = None
    selected_old_title: str | None = None
    selected_old_image_path: str | None = None
    selected_old_kind: str | None = None
    selected_new_sku: str
    selected_new_title: str
    selected_new_image_path: str | None = None
    selected_new_kind: str | None = None
    selected_new_price: float
    recycle_quote: float | None = None
    currency: str | None = None
    qty: int | None = None


class RecommendationSelectResponse(BaseModel):
    session_id: str
    selected: dict[str, Any]
    draft: CheckoutDraft
    next_action: dict[str, str]


class CheckoutFormFieldOption(BaseModel):
    value: str
    label: str


class CheckoutFormField(BaseModel):
    key: str
    label: str
    component: Literal["input", "textarea", "select"]
    type: str | None = None
    required: bool | None = None
    action: str | None = None
    placeholder: str | None = None
    options: list[CheckoutFormFieldOption] | None = None


class CheckoutFormSchema(BaseModel):
    title: str
    submit_label: str
    fields: list[CheckoutFormField]


class CheckoutFormSummary(BaseModel):
    old_lamp: str
    new_lamp: str
    recycle_quote: float
    currency: str
    payable_total_fen: int
    todo: str


class CheckoutFormResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    form_schema: CheckoutFormSchema = Field(alias="schema", serialization_alias="schema")
    defaults: dict[str, str]
    selection: CheckoutDraft
    summary: CheckoutFormSummary


class AddressRequest(BaseModel):
    full_address: str | None = None
    region: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    street: str | None = None
    postal_code: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    location_source: str | None = None
    address_source: str | None = None


class AddressResponse(BaseModel):
    full_address: str
    region: str
    province: str
    city: str
    district: str
    street: str
    postal_code: str
    longitude: float
    latitude: float
    location_source: str
    address_source: str
    validated: bool
    completion_tips: list[str] = Field(default_factory=list)


class CreateOrderUser(BaseModel):
    user_id: str | None = None
    name: str
    phone: str


class CreateOrderItem(BaseModel):
    selected_old_sku: str | None = None
    selected_old_title: str | None = None
    selected_old_image_path: str | None = None
    selected_old_kind: str | None = None
    selected_new_sku: str | None = None
    selected_new_title: str | None = None
    selected_new_image_path: str | None = None
    selected_new_kind: str | None = None
    qty: int = 1


class CreateOrderAddress(AddressRequest):
    full_address: str


class CreateOrderRequest(BaseModel):
    session_id: str
    trace_id: str | None = None
    user: CreateOrderUser
    address: CreateOrderAddress
    items: list[CreateOrderItem]
    payable_total: int
    currency: str = "CNY"
    amount_unit: str = "FEN"
    access_domain: str | None = None


class CreateQrRequest(BaseModel):
    trade_type: Literal["NATIVE", "H5"] = "NATIVE"
    return_url: str | None = None
    idempotent_key: str | None = None


class CreateQrResponse(BaseModel):
    order_id: str
    trace_id: str
    qr_token: str
    code_url: str
    h5_url: str
    expire_at: str
    payable_total: int
    currency: str
    amount_unit: str
    trade_type: str
    mock_mode: bool


class OrderView(BaseModel):
    order_id: str
    trace_id: str
    user_id: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    address_region: str | None = None
    full_address: str | None = None
    receiver_longitude: float | None = None
    receiver_latitude: float | None = None
    location_source: str | None = None
    address_source: str | None = None
    access_domain: str | None = None
    status: str
    order_status: str
    payment_status: str
    pay_status: str
    payable_total: int
    amount_currency: str
    amount_unit: str
    snapshot: dict[str, Any]
    paid_amount_total: int | None = None
    paid_at: str | None = None
    qr_status: str | None = None
    qr_expires_at: str | None = None
    waybill_id: str | None = None
    waybill_status: str | None = None
    prepay_id: str | None = None
    transaction_id: str | None = None
    payment_idempotent_key: str | None = None
    payment_trade_type: str | None = None
    payment_code_url: str | None = None
    payment_h5_url: str | None = None
    payment_updated_at: str | None = None
    wechat_pay_enabled: bool = False
    wechat_pay_configured: bool = False
    qr_token: str | None = None
    recycle_progress: list[dict[str, Any]] = Field(default_factory=list)
    shipment_progress: list[dict[str, Any]] = Field(default_factory=list)
    mock_mode: bool = False
    payment_mode: str = "mock"
    requires_review: bool = False


class ElectronicOrderResponse(BaseModel):
    order_id: str
    trace_id: str
    code: str
    message: str | None = None
    status_code: int
    order_basic: dict[str, Any] | None = None
    items: list[dict[str, Any]] | None = None
    payment: dict[str, Any] | None = None
    waybill: dict[str, Any] | None = None
    timeline: list[dict[str, Any]] | None = None


class LogisticsResponse(BaseModel):
    order_id: str
    waybill_id: str
    status: str
    trace_id: str
    provider: str
    events: list[dict[str, Any]]
    nodes: list[dict[str, Any]]


class LogisticsMapResponse(BaseModel):
    order_id: str
    waybill_id: str
    provider: str
    nodes: list[dict[str, Any]]
    route: list[list[float]]


class TimelineEvent(BaseModel):
    id: int
    request_id: str
    event_type: str
    session_id: str | None = None
    order_id: str | None = None
    payload: dict[str, Any]
    created_at: datetime


class SessionTimelineResponse(BaseModel):
    session_id: str
    events: list[TimelineEvent]


class LampClassificationResponse(BaseModel):
    success: bool
    lamp_type: str
    confidence: float
    label: str | None = None
    score: float | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    model_id: str | None = None
    backend: str | None = None
    image_path: str | None = None
    upload: UploadInfo | None = None
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    session_id: str
    user_id: str
    client_session_id: str | None = None
    stage: Stage = Stage.INIT
    created_at: datetime
    updated_at: datetime
    quote_payload: dict[str, Any] | None = None
    preferences: dict[str, str] = Field(default_factory=dict)
    recommendation_payload: dict[str, Any] | None = None
    selected_recommendation: dict[str, Any] | None = None
    order_id: str | None = None
    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    token_expires_at: datetime


class HealthDependency(BaseModel):
    status: Literal["ok", "error", "degraded"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    request_id: str
    dependencies: dict[str, HealthDependency]
    modes: dict[str, str]


class PreflightCheck(BaseModel):
    ready: bool
    reason: str


class PreflightResponse(BaseModel):
    request_id: str
    quote: PreflightCheck
    classifier: PreflightCheck
    recommendation: PreflightCheck
    payment: PreflightCheck
