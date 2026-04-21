import json
import threading
import unittest
import urllib.request

from image_quote_system.serving.lamp_type_api import LampTypeApiHandler, build_lamp_type_server


class FakeLampClassifier:
    model_id = "fake/lamp-classifier"
    candidate_labels = ["chandelier", "table lamp", "floor lamp"]

    @property
    def backend(self) -> str:
        return "fake-backend"

    def classify(self, image, *, candidate_labels=None, topk=3):
        labels = candidate_labels or list(self.candidate_labels)
        class Result:
            label = labels[0]
            score = 0.91
            model_id = "fake/lamp-classifier"
            backend = "fake-backend"
            candidates = [
                {"label": label, "score": round(0.91 - idx * 0.1, 4)}
                for idx, label in enumerate(labels[:topk])
            ]

            def to_dict(self):
                return {
                    "label": self.label,
                    "score": self.score,
                    "candidates": self.candidates,
                    "model_id": self.model_id,
                    "backend": self.backend,
                }

        return Result()


class LampTypeApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = build_lamp_type_server(host="127.0.0.1", port=0, project_root=".")
        LampTypeApiHandler.classifier = FakeLampClassifier()
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

    def request_multipart(self, path: str, field_name: str, filename: str, content: bytes, extra_fields: dict[str, str] | None = None):
        boundary = "----CodexLampBoundary"
        payload = b""
        if extra_fields:
            for key, value in extra_fields.items():
                payload += (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                    f"{value}\r\n"
                ).encode("utf-8")
        payload += (
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

    def test_health(self):
        payload = self.request_json("/health")
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["backend"], "fake-backend")

    def test_classify_by_path_requires_image_path(self):
        request = urllib.request.Request(
            f"{self.base_url}/classify-lamp",
            data=json.dumps({}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 400)

    def test_classify_upload(self):
        payload = self.request_multipart(
            "/classify-lamp-upload",
            "file",
            "lamp.png",
            self.build_image(),
            extra_fields={"candidate_labels": "chandelier,table lamp,floor lamp", "topk": "2"},
        )
        self.assertEqual(payload["label"], "chandelier")
        self.assertEqual(len(payload["candidates"]), 2)
        self.assertIn("upload", payload)


if __name__ == "__main__":
    unittest.main()
