from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from ..classification import enrich_quote_payload_with_lamp_type
from ..config import load_config
from ..io_utils import ensure_dir


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


FORM_SCHEMA = {
    "title": "Shipping details",
    "submit_label": "Generate payment QR",
    "fields": [
        {
            "key": "name",
            "label": "Receiver name",
            "component": "input",
            "type": "text",
            "required": True,
            "placeholder": "e.g. Alex",
        },
        {
            "key": "phone",
            "label": "Phone",
            "component": "input",
            "type": "tel",
            "required": True,
            "placeholder": "Enter phone number",
        },
        {
            "key": "full_address",
            "label": "Address",
            "component": "textarea",
            "required": True,
            "action": "locate",
            "placeholder": "Enter full address",
        },
    ],
}


@dataclass
class AgentSession:
    session_id: str
    created_at: str = field(default_factory=iso_now)
    updated_at: str = field(default_factory=iso_now)
    stage: str = "await_image"
    quote_payload: dict[str, Any] | None = None
    preferences: dict[str, str] = field(default_factory=dict)
    recommendation_payload: dict[str, Any] | None = None
    selected_recommendation: dict[str, Any] | None = None
    order_id: str | None = None


@dataclass
class AgentOrder:
    order_id: str
    session_id: str
    trace_id: str
    snapshot: dict[str, Any]
    created_at: str = field(default_factory=iso_now)
    updated_at: str = field(default_factory=iso_now)
    status: str = "CREATED"
    order_status: str = "CREATED"
    payment_status: str = "UNPAID"
    pay_status: str = "UNPAID"
    payable_total: int = 0
    amount_currency: str = "CNY"
    amount_unit: str = "FEN"
    qr_status: str | None = None
    qr_token: str | None = None
    qr_expires_at: str | None = None
    payment_updated_at: str | None = None
    paid_at: str | None = None
    waybill_id: str | None = None
    waybill_status: str | None = None
    transaction_id: str | None = None
    mock_mode: bool = True


class AgentBackend:
    def __init__(self) -> None:
        self.sessions: dict[str, AgentSession] = {}
        self.orders: dict[str, AgentOrder] = {}
        self._catalog_cache: list[dict[str, Any]] | None = None
        self._real_image_pool_cache: list[str] | None = None
        self.backend_mode = os.getenv("AI_LIGHT_AGENT_MODE", "real").strip().lower() or "real"

    def ensure_session(self, session_id: str) -> AgentSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = AgentSession(session_id=session_id)
        return self.sessions[session_id]

    def create_session(self, requested_session_id: str | None = None) -> dict[str, Any]:
        session_id = requested_session_id or f"agent_{uuid.uuid4().hex[:12]}"
        session = self.ensure_session(session_id)
        return {"session_id": session.session_id, "state": session.stage, "messages": []}
    def upload_old_lamp(
        self,
        session_id: str,
        raw: bytes,
        filename: str,
        config_dir: str | Path,
    ) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        upload_path = self._save_upload(raw, filename, config_dir)
        quote_payload = self._identify_and_quote(upload_path, config_dir)
        quote_payload["upload"] = {
            "filename": Path(filename).name or upload_path.name,
            "stored_path": str(upload_path.resolve()),
            "size_bytes": len(raw),
        }
        quote_payload = self._compact_quote_payload(quote_payload)

        # Reset downstream state so a newly uploaded image always starts a fresh intent flow.
        session.preferences = {}
        session.recommendation_payload = None
        session.selected_recommendation = None
        session.order_id = None
        session.quote_payload = quote_payload
        session.stage = "collect_preferences"
        session.updated_at = iso_now()

        summary = quote_payload.get("summary") or {}
        recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
        recycle_quote = _coerce_float(summary.get("recycle_quote"), 0.0)
        currency = str(summary.get("currency") or "CNY")
        answer = self._ask_song_qna(
            (
                f"I uploaded an old lamp image. Recognized SKU: {recognized_sku or 'unknown'}. "
                f"Estimated recycle quote: {currency} {recycle_quote:.2f}. "
                "Please continue with replacement advice."
            ),
            session_id=session.session_id,
            recognized_sku=recognized_sku,
        )

        preference_prompt = (
            "请告诉我你的换新需求：安装空间（客厅/卧室/餐厅等）、预算（经济/均衡/高端或金额）、"
            "偏好类型（吊灯/壁灯/落地灯）。我会按你的需求推荐灯具。"
        )
        if answer:
            answer = f"{answer}\n\n{preference_prompt}"
        else:
            answer = preference_prompt

        return {
            "session_id": session.session_id,
            "state": session.stage,
            "messages": [
                {
                    "role": "assistant",
                    "text": answer,
                    "cards": [{"type": "recycle_quote", "data": quote_payload}],
                }
            ],
        }

    def handle_user_message(self, session_id: str, text: str, config_dir: str | Path) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        session.updated_at = iso_now()

        if session.quote_payload and session.stage in {"collect_preferences", "quote_ready"}:
            extracted = self._extract_preferences(text)
            merged_preferences = dict(session.preferences)
            merged_preferences.update(extracted)

            if not self._should_build_recommendations(
                session=session,
                user_text=text,
                merged_preferences=merged_preferences,
            ):
                session.preferences = merged_preferences
                summary = session.quote_payload.get("summary") or {}
                recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
                answer = self._ask_song_qna(
                    self._build_collect_preferences_agent_prompt(user_text=text, session=session),
                    session_id=session.session_id,
                    recognized_sku=recognized_sku,
                )
                if not answer:
                    answer = self._build_collect_preferences_fallback(session.preferences)

                return {
                    "session_id": session.session_id,
                    "state": session.stage,
                    "messages": [{"role": "assistant", "text": answer}],
                }

            session.preferences = merged_preferences

            summary = session.quote_payload.get("summary") or {}
            recognized_type = str(summary.get("recognized_type") or "").strip()
            if not session.preferences.get("install_type"):
                session.preferences["install_type"] = recognized_type or "any"
            if not session.preferences.get("budget_level"):
                session.preferences["budget_level"] = "balanced"
            if not session.preferences.get("space"):
                session.preferences["space"] = "living_room"

            session.recommendation_payload = self._build_recommendations(session, config_dir)
            session.stage = "recommendation_ready"
            session.updated_at = iso_now()
            summary = session.quote_payload.get("summary") or {}
            recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
            rec_prompt = self._build_recommendation_agent_prompt(
                user_text=text,
                session=session,
                recommendation_payload=session.recommendation_payload,
            )
            answer = self._ask_song_qna(
                rec_prompt,
                session_id=session.session_id,
                recognized_sku=recognized_sku,
            )
            if not answer:
                answer = self._ask_song_qna(
                    (
                        f"用户想看换新推荐。偏好：{session.preferences.get('space','')}/"
                        f"{session.preferences.get('budget_level','')}/"
                        f"{session.preferences.get('install_type','')}。"
                        "请用1-2句自然中文引导用户在下方卡片中选择。"
                    ),
                    session_id=session.session_id,
                    recognized_sku=recognized_sku,
                )
            if not answer:
                answer = "我已根据你的偏好准备了推荐方案，请先看下面卡片。"

            return {
                "session_id": session.session_id,
                "state": session.stage,
                "messages": [
                    {
                        "role": "assistant",
                        "text": answer,
                        "cards": [{"type": "replacement_recommendations", "data": session.recommendation_payload}],
                    }
                ],
            }

        summary = (session.quote_payload or {}).get("summary") or {}
        recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
        answer = self._ask_song_qna(text, session_id=session.session_id, recognized_sku=recognized_sku)
        if not answer:
            answer = "智能体服务暂时无响应，请稍后重试。"

        return {
            "session_id": session.session_id,
            "state": session.stage,
            "messages": [{"role": "assistant", "text": answer}],
        }

    def submit_preferences(
        self,
        session_id: str,
        payload: dict[str, Any],
        config_dir: str | Path,
    ) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        if not session.quote_payload:
            raise ValueError("old lamp quote is required before preferences")

        for key in ("install_type", "space", "budget_level"):
            value = str(payload.get(key, "")).strip()
            if value:
                session.preferences[key] = value

        note = str(payload.get("note", "")).strip()
        if note:
            session.preferences["note"] = note

        session.recommendation_payload = self._build_recommendations(session, config_dir)
        session.stage = "recommendation_ready"
        session.updated_at = iso_now()
        summary = (session.quote_payload or {}).get("summary") or {}
        recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
        user_text = "；".join(
            [
                f"space={session.preferences.get('space', '')}",
                f"budget={session.preferences.get('budget_level', '')}",
                f"type={session.preferences.get('install_type', '')}",
                f"note={session.preferences.get('note', '')}",
            ]
        )
        rec_prompt = self._build_recommendation_agent_prompt(
            user_text=user_text,
            session=session,
            recommendation_payload=session.recommendation_payload,
        )
        answer = self._ask_song_qna(
            rec_prompt,
            session_id=session.session_id,
            recognized_sku=recognized_sku,
        )
        if not answer:
            answer = self._ask_song_qna(
                (
                    f"用户已提交偏好：{session.preferences.get('space','')}/"
                    f"{session.preferences.get('budget_level','')}/"
                    f"{session.preferences.get('install_type','')}。"
                    "请用1-2句自然中文引导用户在下方卡片中选择。"
                ),
                session_id=session.session_id,
                recognized_sku=recognized_sku,
            )
        if not answer:
            answer = "已为你准备好推荐方案，请先看下面卡片。"

        return {
            "session_id": session.session_id,
            "state": session.stage,
            "messages": [
                {
                    "role": "assistant",
                    "text": answer,
                    "cards": [{"type": "replacement_recommendations", "data": session.recommendation_payload}],
                }
            ],
        }

    def select_recommendation(self, session_id: str, sku_id: str) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        payload = session.recommendation_payload or {}
        selected = next((item for item in payload.get("recommendations", []) if item.get("sku_id") == sku_id), None)
        if not selected:
            raise ValueError("selected recommendation not found")

        session.selected_recommendation = selected
        session.stage = "checkout_ready"
        session.updated_at = iso_now()

        return {
            "session_id": session.session_id,
            "selected": selected,
            "draft": self._build_checkout_draft(session),
            "next_action": {
                "type": "checkout_form",
                "form_schema_url": f"/agent/forms/checkout?session_id={session.session_id}",
            },
        }

    def get_checkout_form(self, session_id: str) -> dict[str, Any]:
        session = self.ensure_session(session_id)
        if not session.selected_recommendation:
            raise ValueError("recommendation selection is required before checkout")

        draft = self._build_checkout_draft(session)
        return {
            "session_id": session.session_id,
            "schema": FORM_SCHEMA,
            "defaults": self._build_checkout_defaults(session),
            "selection": draft,
            "summary": {
                "old_lamp": draft.get("selected_old_title", ""),
                "new_lamp": draft.get("selected_new_title", ""),
                "recycle_quote": draft.get("recycle_quote", 0.0),
                "currency": draft.get("currency", "CNY"),
                "payable_total_fen": int(round(float(draft.get("selected_new_price") or 0.0) * 100)),
            },
        }

    def normalize_address(self, payload: dict[str, Any]) -> dict[str, Any]:
        full_address = str(payload.get("full_address", "")).strip()
        if not full_address:
            full_address = " ".join(
                [
                    str(payload.get("region", "")).strip(),
                    str(payload.get("province", "")).strip(),
                    str(payload.get("city", "")).strip(),
                    str(payload.get("district", "")).strip(),
                    str(payload.get("street", "")).strip(),
                ]
            ).strip()
        if not full_address:
            raise ValueError("address is required")
        region = str(payload.get("region", "")).strip()
        province = str(payload.get("province", "")).strip()
        city = str(payload.get("city", "")).strip()
        district = str(payload.get("district", "")).strip()
        street = str(payload.get("street", "")).strip()
        postal_code = str(payload.get("postal_code", "")).strip()
        latitude = _coerce_float(payload.get("latitude"), 0.0)
        longitude = _coerce_float(payload.get("longitude"), 0.0)
        location_source = str(payload.get("location_source", "")).strip() or "USER_INPUT"
        address_source = str(payload.get("address_source", "")).strip() or "USER_INPUT"

        completion_tips: list[str] = []
        if not province or not city:
            completion_tips.append("建议补充省市信息，便于物流和配送。")
        if not district:
            completion_tips.append("建议补充区县信息。")
        if not street:
            completion_tips.append("建议补充街道与门牌号。")

        return {
            "full_address": full_address,
            "region": region,
            "province": province,
            "city": city,
            "district": district,
            "street": street,
            "postal_code": postal_code,
            "longitude": longitude,
            "latitude": latitude,
            "location_source": location_source,
            "address_source": address_source,
            "validated": bool(full_address),
            "completion_tips": completion_tips,
        }

    def locate_address(self, payload: dict[str, Any]) -> dict[str, Any]:
        latitude = _coerce_float(payload.get("latitude"), 0.0)
        longitude = _coerce_float(payload.get("longitude"), 0.0)
        manual_address = str(payload.get("full_address", "")).strip()
        reverse = self._reverse_geocode_openstreetmap(latitude, longitude)

        region = str(payload.get("region", "")).strip()
        province = str(payload.get("province", "")).strip()
        city = str(payload.get("city", "")).strip()
        district = str(payload.get("district", "")).strip()
        street = str(payload.get("street", "")).strip()
        postal_code = str(payload.get("postal_code", "")).strip()
        location_source = "BROWSER_GEOLOCATION"
        address_source = "BROWSER_GEOLOCATION"

        if reverse:
            region = reverse.get("region") or region
            province = reverse.get("province") or province
            city = reverse.get("city") or city
            district = reverse.get("district") or district
            street = reverse.get("street") or street
            postal_code = reverse.get("postal_code") or postal_code
            location_source = "OPENSTREETMAP_NOMINATIM"
            address_source = "OPENSTREETMAP_NOMINATIM"

        full_address = manual_address or self._compose_full_address(
            region=region,
            province=province,
            city=city,
            district=district,
            street=street,
        )
        if not full_address and reverse:
            full_address = reverse.get("display_name", "")
        if not full_address and latitude and longitude:
            full_address = f"{latitude:.6f}, {longitude:.6f}"

        completion_tips: list[str] = []
        if not province or not city:
            completion_tips.append("定位成功，但省市信息不完整，建议手动补充。")
        if not street:
            completion_tips.append("定位成功，建议补充详细门牌号。")

        return {
            "full_address": full_address,
            "region": region,
            "province": province,
            "city": city,
            "district": district,
            "street": street,
            "postal_code": postal_code,
            "latitude": latitude,
            "longitude": longitude,
            "location_source": location_source,
            "address_source": address_source,
            "validated": bool(full_address),
            "completion_tips": completion_tips,
        }

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            raise ValueError("session_id is required")
        session = self.ensure_session(session_id)

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        trace_id = f"tr_{uuid.uuid4().hex[:10]}"
        payable_total = int(_coerce_float(payload.get("payable_total"), 0.0))
        if payable_total <= 0:
            selected_price = _coerce_float((session.selected_recommendation or {}).get("base_price"), 0.0)
            payable_total = int(round(selected_price * 100))

        order = AgentOrder(
            order_id=order_id,
            session_id=session_id,
            trace_id=trace_id,
            snapshot=dict(payload),
            payable_total=payable_total,
            amount_currency=str(payload.get("currency") or "CNY"),
            amount_unit=str(payload.get("amount_unit") or "FEN"),
            mock_mode=True,
        )
        self.orders[order_id] = order
        session.order_id = order_id
        session.updated_at = iso_now()
        return self.get_order(order_id, sync=False)

    def create_qr(self, order_id: str, payload: dict[str, Any], app_origin: str) -> dict[str, Any]:
        order = self._require_order(order_id)
        qr_token = uuid.uuid4().hex
        expires_at = utc_now() + timedelta(minutes=10)

        order.qr_token = qr_token
        order.qr_status = "READY"
        order.qr_expires_at = expires_at.isoformat().replace("+00:00", "Z")
        order.payment_updated_at = iso_now()
        order.updated_at = iso_now()

        qr_content = f"{app_origin}/order/{order.order_id}/electronic?qrToken={qr_token}"
        return {
            "order_id": order.order_id,
            "trace_id": order.trace_id,
            "qr_token": qr_token,
            "code_url": qr_content,
            "h5_url": qr_content,
            "expire_at": order.qr_expires_at,
            "qr": {"status": order.qr_status, "expires_at": order.qr_expires_at, "qr_content": qr_content},
            "payable_total": order.payable_total,
            "currency": order.amount_currency,
        }

    def get_order(self, order_id: str, sync: bool = True) -> dict[str, Any]:
        order = self._require_order(order_id)
        if sync:
            self._sync_order(order)
        return {
            "order_id": order.order_id,
            "trace_id": order.trace_id,
            "status": order.status,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "pay_status": order.pay_status,
            "waybill_status": order.waybill_status,
            "waybill_id": order.waybill_id,
            "payable_total": order.payable_total,
            "currency": order.amount_currency,
            "amount_unit": order.amount_unit,
            "qr_status": order.qr_status,
            "qr_token": order.qr_token,
            "qr_expires_at": order.qr_expires_at,
            "snapshot": order.snapshot,
            "mock_mode": order.mock_mode,
        }

    def get_electronic_order(self, order_id: str, qr_token: str) -> dict[str, Any]:
        order = self._require_order(order_id)
        self._sync_order(order)
        if not order.qr_token or order.qr_token != qr_token:
            raise ValueError("qr token not found")
        return {
            "order_id": order.order_id,
            "trace_id": order.trace_id,
            "status": order.order_status,
            "pay_status": order.pay_status,
            "qr_status": order.qr_status,
            "product_info": {"items": [{"qty": 1}]},
            "amount": {
                "payable_total": order.payable_total,
                "paid_amount_total": order.payable_total if order.payment_status == "PAID" else 0,
                "currency": order.amount_currency,
                "amount_unit": order.amount_unit,
            },
            "waybill": {"waybill_id": order.waybill_id or "", "status": order.waybill_status or ""},
            "events": [
                {"time": order.created_at, "desc": "Order created"},
                {"time": order.updated_at, "desc": f"Status: {order.order_status}"},
            ],
        }

    def get_logistics(self, order_id: str) -> dict[str, Any]:
        order = self._require_order(order_id)
        self._sync_order(order)
        nodes = [
            {"lng": 121.4737, "lat": 31.2304, "label": "Recycle center", "status": "created"},
            {"lng": 121.5, "lat": 31.24, "label": "Transit hub", "status": "in_transit"},
            {"lng": 121.544, "lat": 31.221, "label": "Destination", "status": "destination"},
        ]
        events = [
            {"time": order.created_at, "event": "Order created", "status": "CREATED"},
            {"time": order.updated_at, "event": f"Waybill: {order.waybill_status or 'PENDING'}", "status": order.waybill_status or "PENDING"},
        ]
        return {
            "order_id": order.order_id,
            "waybill_id": order.waybill_id or "",
            "status": order.waybill_status or order.order_status,
            "trace_id": order.trace_id,
            "events": events,
            "nodes": nodes,
            "provider": "mock-openstreetmap",
        }

    def get_logistics_map(self, order_id: str) -> dict[str, Any]:
        logistics = self.get_logistics(order_id)
        return {
            "order_id": logistics["order_id"],
            "waybill_id": logistics["waybill_id"],
            "provider": logistics["provider"],
            "nodes": logistics["nodes"],
            "route": [[node["lng"], node["lat"]] for node in logistics["nodes"]],
        }

    def _save_upload(self, raw: bytes, filename: str, config_dir: str | Path) -> Path:
        config = load_config(config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        upload_dir = ensure_dir(root / "artifacts" / "uploads" / "agent-api")
        suffix = Path(filename).suffix or ".png"
        upload_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        upload_path.write_bytes(raw)
        return upload_path

    def _ask_song_qna(
        self,
        question: str,
        *,
        session_id: str | None = None,
        recognized_sku: str | None = None,
        image_url: str | None = None,
    ) -> str | None:
        question = question.strip()
        if not question:
            return None
        qna_url = os.getenv("AI_LIGHT_QNA_URL", "http://127.0.0.1:8080/api/qna/ask").strip()
        if not qna_url:
            return None

        payload_obj: dict[str, Any] = {"question": question}
        if session_id:
            payload_obj["session_id"] = session_id
        if recognized_sku:
            payload_obj["recognized_sku"] = recognized_sku
        if image_url:
            payload_obj["image_url"] = image_url

        timeout_seconds = max(_coerce_float(os.getenv("AI_LIGHT_QNA_TIMEOUT", "20"), 20.0), 1.0)
        payload = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
        request = urllib_request.Request(qna_url, data=payload, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                raw = response.read()
        except (urllib_error.URLError, TimeoutError):
            return None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        candidates: list[str] = []
        if isinstance(parsed, dict):
            for key in ("answer", "text", "message", "content", "reply"):
                value = parsed.get(key)
                if isinstance(value, str):
                    candidates.append(value)
            data = parsed.get("data")
            if isinstance(data, dict):
                for key in ("answer", "text", "message", "content", "reply"):
                    value = data.get(key)
                    if isinstance(value, str):
                        candidates.append(value)
        answer = next((item.strip() for item in candidates if item and item.strip()), "")
        return answer or None

    def _identify_and_quote(self, image_path: Path, config_dir: str | Path) -> dict[str, Any]:
        try:
            from ..pipeline import quote_single_image

            result = quote_single_image(image_path, config_dir=config_dir, topk=3)
            return enrich_quote_payload_with_lamp_type(_build_quote_payload(result), image_path)
        except Exception:
            return self._build_mock_quote(image_path, config_dir)

    def _compact_quote_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        quote = payload.get("quote") or {}
        summary = payload.get("summary") or {}
        upload = payload.get("upload") or {}
        return {
            "quote": {
                "detection_backend": quote.get("detection_backend", ""),
                "currency": quote.get("currency", summary.get("currency", "CNY")),
                "total_quote": quote.get("total_quote", summary.get("recycle_quote", 0.0)),
            },
            "summary": {
                "recognized_type": summary.get("recognized_type", ""),
                "matched_sku_id": summary.get("matched_sku_id", ""),
                "matched_title": summary.get("matched_title", ""),
                "recycle_quote": summary.get("recycle_quote", 0.0),
                "currency": summary.get("currency", "CNY"),
                "detection_backend": summary.get("detection_backend", ""),
            },
            "upload": {
                "filename": upload.get("filename", ""),
                "stored_path": upload.get("stored_path", ""),
                "size_bytes": upload.get("size_bytes", 0),
            },
        }

    def _build_mock_quote(self, image_path: Path, config_dir: str | Path) -> dict[str, Any]:
        catalog = self._load_catalog(config_dir)
        matched = catalog[0]
        recycle_quote = round(float(matched.get("base_price", 0.0)) * 0.28, 2)
        payload = {
            "quote": {
                "image_path": str(image_path),
                "detection_backend": "mock-vision",
                "currency": "CNY",
                "total_quote": recycle_quote,
                "line_items": [
                    {
                        "detection_index": 0,
                        "matched_sku_id": matched.get("sku_id", ""),
                        "title": matched.get("title", ""),
                        "base_price": float(matched.get("base_price", 0.0)),
                        "final_quote": recycle_quote,
                    }
                ],
            },
            "summary": {
                "recognized_type": matched.get("visual_style", ""),
                "matched_sku_id": matched.get("sku_id", ""),
                "matched_title": matched.get("title", ""),
                "recycle_quote": recycle_quote,
                "currency": "CNY",
                "detection_backend": "mock-vision",
            },
            "upload": {"filename": image_path.name, "stored_path": str(image_path), "size_bytes": image_path.stat().st_size},
        }
        return enrich_quote_payload_with_lamp_type(payload, image_path)
    def _build_recommendations(self, session: AgentSession, config_dir: str | Path) -> dict[str, Any]:
        try:
            from ..recommendation import recommend_replacement_lamps

            result = recommend_replacement_lamps(
                reference_sku_id=str((session.quote_payload or {}).get("summary", {}).get("matched_sku_id", "")),
                preferences={
                    "install_type": session.preferences.get("install_type", "any"),
                    "budget_level": session.preferences.get("budget_level", "balanced"),
                    "material": "any",
                },
                config_dir=config_dir,
                limit=3,
            )
            payload = dict(result)
        except Exception:
            payload = self._build_mock_recommendations(config_dir)
        payload["space"] = session.preferences.get("space", "")
        payload["session_id"] = session.session_id
        payload["selection_api"] = {
            "path": f"/agent/sessions/{session.session_id}/recommendations/select",
            "method": "POST",
        }
        for item in payload.get("recommendations", []):
            image_path = self._resolve_recommendation_image(item, config_dir)
            if image_path:
                item["image_path"] = image_path
                item.pop("image_missing", None)
            else:
                item.pop("image_path", None)
                item["image_missing"] = True
        return payload

    def _build_mock_recommendations(self, config_dir: str | Path) -> dict[str, Any]:
        catalog_all = self._load_catalog(config_dir)
        catalog = catalog_all[:3]
        anchor = catalog_all[0] if catalog_all else {
            "sku_id": "",
            "title": "",
            "visual_style": "any",
            "material": "any",
            "size_band": "",
            "craft": "",
            "base_price": 0,
        }
        return {
            "reference": {
                "sku_id": anchor.get("sku_id", ""),
                "title": anchor.get("title", ""),
                "visual_style": anchor.get("visual_style", "any"),
                "material": anchor.get("material", "any"),
                "size_band": anchor.get("size_band", ""),
                "craft": anchor.get("craft", ""),
                "base_price": float(anchor.get("base_price", 0.0)),
            },
            "preferences": {
                "install_type": "any",
                "budget_level": "balanced",
                "material": "any",
            },
            "recommendations": [
                {
                    "sku_id": row.get("sku_id", ""),
                    "title": row.get("title", ""),
                    "image_path": row.get("image_path", ""),
                    "visual_style": row.get("visual_style", ""),
                    "material": row.get("material", ""),
                    "size_band": row.get("size_band", ""),
                    "craft": row.get("craft", ""),
                    "base_price": float(row.get("base_price", 0.0)),
                    "fit_score": round(max(0.72, 0.94 - idx * 0.08), 2),
                    "recommendation_reasons": ["Matched by catalog similarity"],
                    "suitable_spaces": ["living_room"],
                }
                for idx, row in enumerate(catalog)
            ],
        }

    def _should_build_recommendations(
        self,
        *,
        session: AgentSession,
        user_text: str,
        merged_preferences: dict[str, str],
    ) -> bool:
        if all(merged_preferences.get(key) for key in ("install_type", "space", "budget_level")):
            return True

        summary = (session.quote_payload or {}).get("summary") or {}
        recognized_sku = str(summary.get("matched_sku_id") or "").strip() or None
        pref_desc = (
            f"space={merged_preferences.get('space','')}, "
            f"budget={merged_preferences.get('budget_level','')}, "
            f"type={merged_preferences.get('install_type','')}"
        )
        prompt = (
            "你是对话流程路由器。"
            "请判断用户这句话是否已经明确要求“现在进入推荐灯具阶段”。"
            "只输出严格 JSON：{\"route\":\"recommend\"|\"chat\",\"confidence\":0-1,\"reason\":\"<=20字\"}。"
            f"\n用户输入：{user_text}"
            f"\n当前识别旧灯：SKU={summary.get('matched_sku_id','')}, "
            f"type={summary.get('recognized_type','')}, "
            f"回收价={summary.get('currency','CNY')} {summary.get('recycle_quote', 0)}"
            f"\n当前已收集偏好：{pref_desc}"
        )
        decision = self._ask_song_qna(
            prompt,
            session_id=session.session_id,
            recognized_sku=recognized_sku,
        )
        return self._parse_recommend_route(decision) == "recommend"

    def _parse_recommend_route(self, decision: str | None) -> str:
        if not decision:
            return "chat"
        raw = decision.strip()
        if not raw:
            return "chat"
        try:
            parsed = json.loads(raw)
            route = str((parsed or {}).get("route", "")).strip().lower()
            return "recommend" if route == "recommend" else "chat"
        except json.JSONDecodeError:
            pass

        # tolerate wrapped json text from some LLM gateways
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return "chat"
        try:
            parsed = json.loads(match.group(0))
            route = str((parsed or {}).get("route", "")).strip().lower()
            return "recommend" if route == "recommend" else "chat"
        except json.JSONDecodeError:
            return "chat"

    def _build_collect_preferences_agent_prompt(self, *, user_text: str, session: AgentSession) -> str:
        summary = (session.quote_payload or {}).get("summary") or {}
        missing = self._list_missing_preferences(session.preferences)
        pref_desc = (
            f"space={session.preferences.get('space','')}, "
            f"budget={session.preferences.get('budget_level','')}, "
            f"type={session.preferences.get('install_type','')}"
        )
        return (
            "你是灯具换新智能体。"
            "请先准确回复用户这句话的真实意图，不要只输出模板话术。"
            "如果用户还没给全偏好，再补一句引导其继续补充空间、预算、类型。"
            f"\n用户输入：{user_text}"
            f"\n旧灯识别：SKU={summary.get('matched_sku_id','')}, "
            f"type={summary.get('recognized_type','')}, "
            f"回收价={summary.get('currency','CNY')} {summary.get('recycle_quote', 0)}"
            f"\n当前偏好：{pref_desc}"
            f"\n待补充：{'、'.join(missing) if missing else '无'}"
        )

    def _build_collect_preferences_fallback(self, preferences: dict[str, str]) -> str:
        missing = self._list_missing_preferences(preferences)
        if not missing:
            return "我理解你的意思了。要现在按当前偏好给你推荐可选灯具吗？"
        return (
            "我理解你的意思。为了给你更准确的换新推荐，"
            f"还需要补充：{'、'.join(missing)}。"
        )

    def _list_missing_preferences(self, preferences: dict[str, str]) -> list[str]:
        required_fields = [
            ("space", "安装空间"),
            ("budget_level", "预算范围"),
            ("install_type", "偏好类型"),
        ]
        return [label for key, label in required_fields if not preferences.get(key)]

    def _compose_full_address(
        self,
        *,
        region: str = "",
        province: str = "",
        city: str = "",
        district: str = "",
        street: str = "",
    ) -> str:
        parts: list[str] = []
        for piece in (region, province, city, district, street):
            value = str(piece or "").strip()
            if value and (not parts or parts[-1] != value):
                parts.append(value)
        return " ".join(parts)

    def _reverse_geocode_openstreetmap(self, latitude: float, longitude: float) -> dict[str, str] | None:
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
                "User-Agent": "ai-light-assistant/1.0 (openstreetmap-nominatim)",
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
        if not isinstance(payload, dict):
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
        street = " ".join(part for part in (road, house_number) if part).strip()

        return {
            "region": str(address.get("country_code", "")).upper(),
            "province": pick("state", "province", "region"),
            "city": pick("city", "town", "municipality", "county", "village"),
            "district": pick("city_district", "district", "county", "suburb", "neighbourhood"),
            "street": street,
            "postal_code": pick("postcode"),
            "display_name": str(payload.get("display_name", "")).strip(),
        }

    def _extract_preferences(self, text: str) -> dict[str, str]:
        lowered = text.lower()
        prefs: dict[str, str] = {}

        if any(k in text for k in ("吊灯", "吊装")) or "pendant" in lowered:
            prefs["install_type"] = "pendant"
        elif any(k in text for k in ("壁灯", "墙灯")) or "wall" in lowered:
            prefs["install_type"] = "wall"
        elif any(k in text for k in ("落地灯", "地灯")) or "floor" in lowered:
            prefs["install_type"] = "floor"
        elif any(k in text for k in ("都可以", "随意")) or "any" in lowered:
            prefs["install_type"] = "any"

        if "客厅" in text:
            prefs["space"] = "living_room"
        elif any(k in text for k in ("餐厅", "饭厅")):
            prefs["space"] = "dining_room"
        elif "卧室" in text:
            prefs["space"] = "bedroom"
        elif any(k in text for k in ("办公室", "书房", "办公")):
            prefs["space"] = "office"
        elif any(k in text for k in ("门店", "店里", "展厅", "商铺")):
            prefs["space"] = "store"

        if any(k in text for k in ("经济", "便宜", "性价比", "预算低", "省钱")) or any(
            k in lowered for k in ("economy", "cheap", "budget")
        ):
            prefs["budget_level"] = "economy"
        elif any(k in text for k in ("高端", "豪华", "品质", "预算高", "贵一点")) or any(
            k in lowered for k in ("premium", "high-end", "luxury")
        ):
            prefs["budget_level"] = "premium"
        elif any(k in text for k in ("均衡", "适中", "中等")) or any(
            k in lowered for k in ("balanced", "middle", "mid")
        ):
            prefs["budget_level"] = "balanced"
        else:
            numbers = [int(v) for v in re.findall(r"\d+", text)]
            if numbers:
                amount = max(numbers)
                if amount <= 500:
                    prefs["budget_level"] = "economy"
                elif amount >= 2000:
                    prefs["budget_level"] = "premium"
                else:
                    prefs["budget_level"] = "balanced"

        return prefs

    def _build_recommendation_agent_prompt(
        self,
        *,
        user_text: str,
        session: AgentSession,
        recommendation_payload: dict[str, Any],
    ) -> str:
        summary = (session.quote_payload or {}).get("summary") or {}
        recs = recommendation_payload.get("recommendations") or []
        rec_lines: list[str] = []
        for idx, item in enumerate(recs[:3], 1):
            rec_lines.append(
                f"{idx}.{item.get('title','')}(SKU:{item.get('sku_id','')},"
                f"{item.get('base_price', 0)}元,{item.get('visual_style','')})"
            )

        pref_desc = (
            f"space={session.preferences.get('space','')}, "
            f"budget={session.preferences.get('budget_level','')}, "
            f"type={session.preferences.get('install_type','')}"
        )
        return (
            "你是灯具换新智能体。"
            "请用1-2句自然中文推荐并引导用户在下方卡片中点选，不要模板化。"
            f"\n用户输入：{user_text}"
            f"\n旧灯识别：SKU={summary.get('matched_sku_id','')}, "
            f"type={summary.get('recognized_type','')}, "
            f"回收价={summary.get('currency','CNY')} {summary.get('recycle_quote', 0)}"
            f"\n用户偏好：{pref_desc}"
            f"\n候选灯具：{'; '.join(rec_lines) if rec_lines else '无'}"
        )

    def _resolve_recommendation_image(self, payload: dict[str, Any], config_dir: str | Path) -> str | None:
        candidate = self._validate_catalog_image(payload.get("image_path"), config_dir)
        if candidate and not self._looks_like_placeholder_catalog_image(candidate):
            return candidate
        seed = str(payload.get("sku_id") or payload.get("title") or candidate or "lamp")
        return self._pick_real_recommendation_image(seed, config_dir) or candidate

    def _validate_catalog_image(self, raw_path: Any, config_dir: str | Path) -> str | None:
        candidate = str(raw_path or "").strip()
        if not candidate:
            return None
        project_root = Path(load_config(config_dir)["project"]["root_dir"]).resolve()
        image_path = (project_root / candidate).resolve()
        try:
            image_path.relative_to(project_root)
        except ValueError:
            return None
        if not image_path.is_file():
            return None
        return candidate

    def _looks_like_placeholder_catalog_image(self, image_path: str) -> bool:
        normalized = image_path.replace("\\", "/").lower()
        return normalized.startswith("data/catalog/images/")

    def _pick_real_recommendation_image(self, seed: str, config_dir: str | Path) -> str | None:
        pool = self._get_real_recommendation_images(config_dir)
        if not pool:
            return None
        digest = hashlib.md5(seed.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(pool)
        return pool[index]

    def _get_real_recommendation_images(self, config_dir: str | Path) -> list[str]:
        if self._real_image_pool_cache is not None:
            return self._real_image_pool_cache
        project_root = Path(load_config(config_dir)["project"]["root_dir"]).resolve()
        search_dirs = [
            project_root / "images",
            project_root / "artifacts" / "uploads" / "vision-api",
        ]
        pool: list[str] = []
        for directory in search_dirs:
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*")):
                if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                try:
                    relative = path.resolve().relative_to(project_root).as_posix()
                except ValueError:
                    continue
                pool.append(relative)
        self._real_image_pool_cache = pool
        return pool

    def _load_catalog(self, config_dir: str | Path) -> list[dict[str, Any]]:
        if self._catalog_cache is not None:
            return self._catalog_cache
        project_root = Path(load_config(config_dir)["project"]["root_dir"]).resolve()
        catalog_path = project_root / "data" / "catalog" / "catalog.csv"
        rows: list[dict[str, Any]] = []
        if catalog_path.is_file():
            with catalog_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rows.append(row)
        if not rows:
            rows = [
                {
                    "sku_id": "SKU-DEFAULT-001",
                    "title": "Default Lamp",
                    "image_path": "",
                    "visual_style": "pendant",
                    "material": "metal",
                    "base_price": "299",
                }
            ]
        self._catalog_cache = rows
        return rows

    def _build_checkout_draft(self, session: AgentSession) -> dict[str, Any]:
        quote = session.quote_payload or {}
        summary = quote.get("summary") or {}
        selection = session.selected_recommendation or {}
        return {
            "selected_old_sku": summary.get("matched_sku_id"),
            "selected_old_title": summary.get("matched_title"),
            "selected_old_image_path": ((quote.get("upload") or {}).get("stored_path")) or None,
            "selected_old_kind": summary.get("recognized_type"),
            "selected_new_sku": selection.get("sku_id"),
            "selected_new_title": selection.get("title"),
            "selected_new_image_path": selection.get("image_path"),
            "selected_new_kind": selection.get("visual_style"),
            "selected_new_price": float(selection.get("base_price") or 0.0),
            "recycle_quote": float(summary.get("recycle_quote") or 0.0),
            "currency": summary.get("currency", "CNY"),
            "qty": 1,
        }

    def _build_checkout_defaults(self, session: AgentSession) -> dict[str, Any]:
        draft = self._build_checkout_draft(session)
        return {
            "session_id": session.session_id,
            "trace_id": f"tr_{uuid.uuid4().hex[:10]}",
            "selected_old_sku": draft.get("selected_old_sku") or "",
            "selected_new_sku": draft.get("selected_new_sku") or "",
            "qty": "1",
            "payable_total": str(int(round(float(draft.get("selected_new_price") or 0.0) * 100))),
        }

    def _sync_order(self, order: AgentOrder) -> None:
        now = utc_now()
        prepay_at = _parse_iso(order.payment_updated_at) if order.payment_updated_at else None
        if order.qr_status == "READY" and prepay_at and now - prepay_at >= timedelta(seconds=6):
            order.payment_status = "PAID"
            order.pay_status = "PAID"
            order.order_status = "PAID"
            order.status = "PAID"
            order.paid_at = order.paid_at or iso_now()
            order.transaction_id = order.transaction_id or f"wx_{uuid.uuid4().hex[:12]}"
            order.qr_status = "SCANNED"
            order.waybill_id = order.waybill_id or f"wb_{uuid.uuid4().hex[:10]}"
            order.waybill_status = order.waybill_status or "CREATED"
            order.updated_at = iso_now()
        paid_at = _parse_iso(order.paid_at) if order.paid_at else None
        if paid_at and now - paid_at >= timedelta(seconds=3):
            order.order_status = "FULFILLING"
            order.status = "FULFILLING"
            order.waybill_status = "PICKED_UP"
        if paid_at and now - paid_at >= timedelta(seconds=7):
            order.order_status = "IN_TRANSIT"
            order.status = "IN_TRANSIT"
            order.waybill_status = "IN_TRANSIT"
        if paid_at and now - paid_at >= timedelta(seconds=12):
            order.order_status = "DELIVERING"
            order.status = "DELIVERING"
            order.waybill_status = "OUT_FOR_DELIVERY"
        order.updated_at = iso_now()

    def _require_order(self, order_id: str) -> AgentOrder:
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("order not found")
        return order


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_quote_payload(result: Any) -> dict[str, Any]:
    payload = result.to_dict()
    first_line_item = payload["line_items"][0] if payload.get("line_items") else None
    return {
        "quote": payload,
        "summary": {
            "recognized_type": first_line_item["matched_product"]["metadata"].get("visual_style", "") if first_line_item else "",
            "matched_sku_id": first_line_item["matched_sku_id"] if first_line_item else "",
            "matched_title": first_line_item["title"] if first_line_item else "",
            "recycle_quote": payload.get("total_quote", 0.0),
            "currency": payload.get("currency", "CNY"),
            "detection_backend": payload.get("detection_backend", ""),
        },
    }

