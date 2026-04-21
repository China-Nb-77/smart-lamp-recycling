import io
import json
import os
import threading
import unittest
import urllib.parse
import urllib.request

from image_quote_system.serving.agent_backend import AgentBackend
from image_quote_system.serving.api import QuoteApiHandler, build_server


class AgentApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["AI_LIGHT_AGENT_MODE"] = "mock"
        QuoteApiHandler.agent_backend = AgentBackend()
        QuoteApiHandler.lamp_type_classifier = _FakeLampClassifier()
        cls.server = build_server(host="127.0.0.1", port=0, config_dir="configs")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request_json(self, path: str, method: str = "GET", body: dict | None = None):
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method, headers=headers)
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def request_multipart(self, path: str, field_name: str, filename: str, content: bytes):
        boundary = "----CodexBoundary12345"
        payload = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def build_image(self) -> bytes:
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?"
            b"\x00\x05\xfe\x02\xfeA\xd9\xb4\xa6\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def test_00_lamp_type_upload_api(self):
        payload = self.request_multipart(
            "/classify-lamp-upload",
            "file",
            "lamp.png",
            self.build_image(),
        )
        self.assertEqual(payload["label"], "chandelier")
        self.assertIn("upload", payload)

    def prepare_session(self):
        session_id = "test-session"
        self.request_json("/agent/sessions", method="POST", body={"session_id": session_id})
        upload = self.request_multipart(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/image",
            "file",
            "lamp.png",
            self.build_image(),
        )
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/messages",
            method="POST",
            body={"text": "吊灯"},
        )
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/messages",
            method="POST",
            body={"text": "客厅"},
        )
        recommend = self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/messages",
            method="POST",
            body={"text": "性价比优先"},
        )
        recommendation_card = recommend["messages"][0]["cards"][0]["data"]
        selected_sku = recommendation_card["recommendations"][0]["sku_id"]
        return session_id, upload, recommendation_card, selected_sku

    def test_01_image_upload_recognition_api(self):
        session_id = "upload-session"
        self.request_json("/agent/sessions", method="POST", body={"session_id": session_id})
        payload = self.request_multipart(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/image",
            "file",
            "old-lamp.png",
            self.build_image(),
        )
        self.assertEqual(payload["session_id"], session_id)
        self.assertEqual(payload["messages"][0]["cards"][0]["type"], "recycle_quote")

    def test_02_quote_api(self):
        payload = self.request_multipart("/quote-upload", "file", "quote.png", self.build_image())
        self.assertIn("summary", payload)
        self.assertGreater(payload["summary"]["recycle_quote"], 0)

    def test_03_recommend_api(self):
        payload = self.request_json(
            "/recommend",
            method="POST",
            body={
                "reference_sku_id": "SKU-ALU-PENDANT-S",
                "preferences": {
                    "install_type": "pendant",
                    "budget_level": "economy",
                    "material": "any",
                },
                "limit": 3,
            },
        )
        self.assertIn("recommendations", payload)
        self.assertGreaterEqual(len(payload["recommendations"]), 1)

    def test_04_agent_session_api(self):
        session_id, _, recommendation_card, _ = self.prepare_session()
        self.assertEqual(recommendation_card["session_id"], session_id)
        self.assertGreaterEqual(len(recommendation_card["recommendations"]), 1)

    def test_05_form_submit_api(self):
        session_id, upload, _, selected_sku = self.prepare_session()
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/recommendations/select",
            method="POST",
            body={"sku_id": selected_sku},
        )
        form = self.request_json(
            f"/agent/forms/checkout?session_id={urllib.parse.quote(session_id)}",
        )
        order = self.request_json(
            "/agent/orders",
            method="POST",
            body={
                "session_id": session_id,
                "trace_id": "trace_test",
                "user": {"name": "Test User", "phone": "13800000000"},
                "address": {
                    "full_address": "上海市浦东新区张江路 88 号",
                    "region": "shanghai",
                    "city": "上海市",
                    "district": "浦东新区",
                },
                "items": [
                    {
                        "selected_old_sku": upload["messages"][0]["cards"][0]["data"]["summary"]["matched_sku_id"],
                        "selected_new_sku": form["selection"]["selected_new_sku"],
                        "qty": 1,
                    }
                ],
                "payable_total": form["summary"]["payable_total_fen"],
                "currency": "CNY",
                "amount_unit": "FEN",
                "access_domain": "http://localhost:5173",
            },
        )
        self.assertIn("order_id", order)
        self.order_id = order["order_id"]

    def test_06_qr_order_api(self):
        session_id, upload, _, selected_sku = self.prepare_session()
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/recommendations/select",
            method="POST",
            body={"sku_id": selected_sku},
        )
        form = self.request_json(f"/agent/forms/checkout?session_id={urllib.parse.quote(session_id)}")
        order = self.request_json(
            "/agent/orders",
            method="POST",
            body={
                "session_id": session_id,
                "trace_id": "trace_test_qr",
                "user": {"name": "Test User", "phone": "13800000000"},
                "address": {"full_address": "上海市浦东新区张江路 88 号"},
                "items": [
                    {
                        "selected_old_sku": upload["messages"][0]["cards"][0]["data"]["summary"]["matched_sku_id"],
                        "selected_new_sku": form["selection"]["selected_new_sku"],
                        "qty": 1,
                    }
                ],
                "payable_total": form["summary"]["payable_total_fen"],
                "currency": "CNY",
                "amount_unit": "FEN",
            },
        )
        qr = self.request_json(
            f"/agent/orders/{urllib.parse.quote(order['order_id'])}/qr",
            method="POST",
            body={"trade_type": "NATIVE", "return_url": "http://localhost:5173/payment/success"},
        )
        self.assertIn("qr_token", qr)
        self.assertIn("code_url", qr)

    def test_07_order_status_api(self):
        session_id, upload, _, selected_sku = self.prepare_session()
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/recommendations/select",
            method="POST",
            body={"sku_id": selected_sku},
        )
        form = self.request_json(f"/agent/forms/checkout?session_id={urllib.parse.quote(session_id)}")
        order = self.request_json(
            "/agent/orders",
            method="POST",
            body={
                "session_id": session_id,
                "trace_id": "trace_test_status",
                "user": {"name": "Test User", "phone": "13800000000"},
                "address": {"full_address": "上海市浦东新区张江路 88 号"},
                "items": [
                    {
                        "selected_old_sku": upload["messages"][0]["cards"][0]["data"]["summary"]["matched_sku_id"],
                        "selected_new_sku": form["selection"]["selected_new_sku"],
                        "qty": 1,
                    }
                ],
                "payable_total": form["summary"]["payable_total_fen"],
                "currency": "CNY",
                "amount_unit": "FEN",
            },
        )
        status = self.request_json(f"/agent/orders/{urllib.parse.quote(order['order_id'])}?sync=true")
        self.assertEqual(status["order_id"], order["order_id"])

    def test_08_logistics_api(self):
        session_id, upload, _, selected_sku = self.prepare_session()
        self.request_json(
            f"/agent/sessions/{urllib.parse.quote(session_id)}/recommendations/select",
            method="POST",
            body={"sku_id": selected_sku},
        )
        form = self.request_json(f"/agent/forms/checkout?session_id={urllib.parse.quote(session_id)}")
        order = self.request_json(
            "/agent/orders",
            method="POST",
            body={
                "session_id": session_id,
                "trace_id": "trace_test_logistics",
                "user": {"name": "Test User", "phone": "13800000000"},
                "address": {"full_address": "上海市浦东新区张江路 88 号"},
                "items": [
                    {
                        "selected_old_sku": upload["messages"][0]["cards"][0]["data"]["summary"]["matched_sku_id"],
                        "selected_new_sku": form["selection"]["selected_new_sku"],
                        "qty": 1,
                    }
                ],
                "payable_total": form["summary"]["payable_total_fen"],
                "currency": "CNY",
                "amount_unit": "FEN",
            },
        )
        self.request_json(
            f"/agent/orders/{urllib.parse.quote(order['order_id'])}/qr",
            method="POST",
            body={"trade_type": "NATIVE", "return_url": "http://localhost:5173/payment/success"},
        )
        logistics = self.request_json(f"/agent/orders/{urllib.parse.quote(order['order_id'])}/logistics")
        logistics_map = self.request_json(
            f"/agent/orders/{urllib.parse.quote(order['order_id'])}/logistics-map"
        )
        self.assertIn("events", logistics)
        self.assertIn("route", logistics_map)


class _FakeLampClassifier:
    model_id = "fake/lamp-model"
    candidate_labels = ["chandelier", "wall lamp", "floor lamp"]

    @property
    def backend(self) -> str:
        return "fake-backend"

    def classify(self, image, *, candidate_labels=None, topk=3):
        labels = candidate_labels or self.candidate_labels
        return type(
            "FakeResult",
            (),
            {
                "to_dict": lambda self: {
                    "label": labels[0],
                    "score": 0.92,
                    "candidates": [
                        {"label": label, "score": round(0.92 - idx * 0.1, 4)}
                        for idx, label in enumerate(labels[:topk])
                    ],
                    "model_id": "fake/lamp-model",
                    "backend": "fake-backend",
                }
            },
        )()


if __name__ == "__main__":
    unittest.main()
