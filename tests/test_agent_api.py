from __future__ import annotations

import os
from importlib import import_module, reload
import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.llm import LLMDecision
from backend.app.models import QuoteResponse, QuoteSummary, UploadInfo
from backend.app.service import FOLLOW_UP_QUESTIONS


def build_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def build_client(tmp_path: Path) -> TestClient:
    os.environ["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'agent-test.db').as_posix()}"
    os.environ["REDIS_URL"] = "fakeredis://local"
    os.environ["AI_LIGHT_WORKFLOW_MODE"] = "mock"
    os.environ["AI_LIGHT_PAYMENT_MODE"] = "mock"
    os.environ["AI_LIGHT_ALLOW_REVIEW_FALLBACK"] = "true"
    module = reload(import_module("backend.app.main"))
    return TestClient(module.create_app())


def create_session(client: TestClient, client_session_id: str = "local-session-1") -> dict:
    response = client.post("/agent/sessions", json={"client_session_id": client_session_id})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["session_id"] != client_session_id
    assert payload["session_token"]
    return payload


def auth_headers(session_payload: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_payload['session_token']}"}


def fake_decision(
    reply: str,
    *,
    intent: str,
    slots: dict | None = None,
    confidence: float = 0.92,
) -> LLMDecision:
    return LLMDecision(
        reply=reply,
        intent=intent,
        confidence=confidence,
        slots=slots or {},
        trace={
            "model": "fake-siliconflow",
            "prompt": [],
            "response": "",
            "latency": 1,
            "provider_response": "{}",
            "prompt_version": "test",
        },
    )


def test_server_issues_session_id_and_token(tmp_path: Path):
    client = build_client(tmp_path)
    payload = create_session(client, client_session_id="browser-local-id")
    assert payload["state"] == "init"
    assert payload["user_id"].startswith("guest_")


def test_review_fallback_requires_manual_review_and_blocks_checkout(tmp_path: Path):
    client = build_client(tmp_path)
    service = client.app.state.context.service
    decisions = [
        fake_decision(
            "旧灯图我已经收到，但当前识别结果需要人工复核。我先记住你的偏好，继续给你看目录推荐。",
            intent="collect_pref",
        ),
        fake_decision(
            "我先按你的需求给你看目录推荐，不过这次识别还在人工复核里，所以不会直接开放下单。",
            intent="recommend",
            slots={"space": "living_room", "budget_level": "balanced", "install_type": "pendant"},
        ),
    ]
    service.agent_brain.decide = lambda **kwargs: decisions.pop(0)  # type: ignore[method-assign]
    session = create_session(client, client_session_id="review-flow")

    upload = client.post(
        f"/agent/sessions/{session['session_id']}/image",
        headers=auth_headers(session),
        files={"file": ("lamp.png", build_png(), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    upload_payload = upload.json()
    quote_card = upload_payload["messages"][0]["cards"][0]["data"]
    assert quote_card["summary"]["requires_review"] is True
    assert quote_card["summary"]["checkout_allowed"] is False

    recommend = client.post(
        f"/agent/sessions/{session['session_id']}/preferences",
        headers=auth_headers(session),
        json={
            "space": "living_room",
            "budget_level": "balanced",
            "install_type": "pendant",
        },
    )
    assert recommend.status_code == 200, recommend.text
    rec_payload = recommend.json()["messages"][0]["cards"][0]["data"]
    assert rec_payload["source"] == "catalog"
    assert rec_payload["requires_review"] is True
    assert rec_payload["checkout_allowed"] is False

    sku_id = rec_payload["recommendations"][0]["sku_id"]
    blocked = client.post(
        f"/agent/sessions/{session['session_id']}/recommendations/select",
        headers=auth_headers(session),
        json={"sku_id": sku_id},
    )
    assert blocked.status_code == 412, blocked.text
    assert blocked.json()["code"] == "requires_review"


def test_non_review_session_can_create_order_and_qr(tmp_path: Path):
    client = build_client(tmp_path)
    service = client.app.state.context.service
    decisions = [
        fake_decision(
            "旧灯我先识别好了，你前面提到的需求我也记下来了，我直接给你筛推荐。",
            intent="recommend",
            slots={"space": "living_room", "budget_level": "balanced", "install_type": "pendant"},
        ),
        fake_decision(
            "我已经整理好你的偏好，下面给你看推荐结果。",
            intent="recommend",
            slots={"space": "living_room", "budget_level": "balanced", "install_type": "pendant"},
        ),
    ]
    service.agent_brain.decide = lambda **kwargs: decisions.pop(0)  # type: ignore[method-assign]

    def safe_quote(*, image_path, request_id):
        return QuoteResponse(
            quote={
                "image_path": str(image_path),
                "detection_backend": "unit-test",
                "embedding_backend": "unit-test",
                "retrieval_backend": "catalog-rules",
                "currency": "CNY",
                "total_quote": 88.0,
                "price_summary": {
                    "line_item_count": 1,
                    "subtotal_before_residual": 88.0,
                    "residual_total": 0.0,
                    "total_quote": 88.0,
                    "currency": "CNY",
                },
                "detection_summary": {
                    "backend": "unit-test",
                    "used_fallback": False,
                    "notes": [],
                    "detections": [],
                },
                "line_items": [
                    {
                        "detection_index": 0,
                        "matched_sku_id": "SKU-ALU-PENDANT-S",
                        "title": "Aluminum Pendant Lamp",
                        "base_price": 299.0,
                        "final_quote": 88.0,
                        "similarity_score": 0.99,
                        "detection_confidence": 0.95,
                        "matched_product": {"metadata": {"visual_style": "pendant"}},
                        "topk_similar_items": [],
                        "breakdown": {},
                        "price_composition": {},
                    }
                ],
            },
            summary=QuoteSummary(
                recognized_type="pendant",
                matched_sku_id="SKU-ALU-PENDANT-S",
                matched_title="Aluminum Pendant Lamp",
                recycle_quote=88.0,
                currency="CNY",
                detection_backend="unit-test",
                requires_review=False,
                review_reasons=[],
                checkout_allowed=True,
            ),
            follow_up_questions=FOLLOW_UP_QUESTIONS,
            upload=UploadInfo(filename="lamp.png", stored_path="artifacts/uploads/agent-api/test.png", size_bytes=67),
        )

    service.quote_image = safe_quote  # type: ignore[method-assign]

    session = create_session(client, client_session_id="happy-flow")
    upload = client.post(
        f"/agent/sessions/{session['session_id']}/image",
        headers=auth_headers(session),
        files={"file": ("lamp.png", build_png(), "image/png")},
    )
    assert upload.status_code == 200, upload.text

    recommend = client.post(
        f"/agent/sessions/{session['session_id']}/preferences",
        headers=auth_headers(session),
        json={
            "space": "living_room",
            "budget_level": "balanced",
            "install_type": "pendant",
        },
    )
    assert recommend.status_code == 200, recommend.text
    recommendations = recommend.json()["messages"][0]["cards"][0]["data"]
    sku_id = recommendations["recommendations"][0]["sku_id"]

    selected = client.post(
        f"/agent/sessions/{session['session_id']}/recommendations/select",
        headers=auth_headers(session),
        json={"sku_id": sku_id},
    )
    assert selected.status_code == 200, selected.text

    checkout = client.get(
        f"/agent/forms/checkout?session_id={session['session_id']}",
        headers=auth_headers(session),
    )
    assert checkout.status_code == 200, checkout.text
    checkout_payload = checkout.json()
    assert "todo" in checkout_payload["summary"]

    order = client.post(
        "/agent/orders",
        headers=auth_headers(session),
        json={
            "session_id": session["session_id"],
            "trace_id": "trace_test_happy",
            "user": {"user_id": "user-1", "name": "Test User", "phone": "13800000000"},
            "address": {
                "full_address": "上海市浦东新区测试路 100 号",
                "region": "CN",
                "province": "上海市",
                "city": "上海市",
                "district": "浦东新区",
                "street": "测试路 100 号",
                "longitude": 121.544,
                "latitude": 31.221,
                "location_source": "USER_INPUT",
                "address_source": "USER_INPUT",
            },
            "items": [
                {
                    "selected_old_sku": "SKU-ALU-PENDANT-S",
                    "selected_new_sku": checkout_payload["selection"]["selected_new_sku"],
                    "qty": 1,
                }
            ],
            "payable_total": checkout_payload["summary"]["payable_total_fen"],
            "currency": "CNY",
            "amount_unit": "FEN",
            "access_domain": "http://localhost:5173",
        },
    )
    assert order.status_code == 200, order.text
    order_payload = order.json()
    assert order_payload["order_id"].startswith("ord_")
    assert order_payload["snapshot"]["session_id"] == session["session_id"]

    qr = client.post(
        f"/agent/orders/{order_payload['order_id']}/qr",
        json={"trade_type": "NATIVE", "return_url": "http://localhost:5173/payment/success"},
    )
    assert qr.status_code == 200, qr.text
    qr_payload = qr.json()
    assert qr_payload["qr_token"]
    assert qr_payload["mock_mode"] is True

    timeline = client.get(
        f"/agent/sessions/{session['session_id']}/timeline",
        headers=auth_headers(session),
    )
    assert timeline.status_code == 200, timeline.text
    assert len(timeline.json()["events"]) >= 4
