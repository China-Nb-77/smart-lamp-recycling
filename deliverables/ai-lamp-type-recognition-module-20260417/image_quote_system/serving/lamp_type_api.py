from __future__ import annotations

import io
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..classification import DEFAULT_LAMP_LABELS, OpenSourceLampTypeClassifier
from ..io_utils import ensure_dir


class LampTypeApiHandler(BaseHTTPRequestHandler):
    project_root = Path(".").resolve()
    classifier = OpenSourceLampTypeClassifier()

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "backend": self.classifier.backend,
                        "model_id": self.classifier.model_id,
                        "default_candidate_labels": list(self.classifier.candidate_labels),
                    },
                )
                return
            self._send_json(404, {"error": "not found"})
        except Exception as exc:  # pragma: no cover
            self._send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/classify-lamp":
                self._handle_classify_by_path()
                return
            if parsed.path == "/classify-lamp-upload":
                self._handle_classify_upload()
                return
            self._send_json(404, {"error": "not found"})
        except Exception as exc:  # pragma: no cover
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_classify_by_path(self) -> None:
        payload = self._read_json_body()
        image_path = str(payload.get("image_path", "")).strip()
        if not image_path:
            self._send_json(400, {"error": "image_path is required"})
            return

        resolved = Path(image_path)
        if not resolved.is_absolute():
            resolved = (self.project_root / resolved).resolve()
        if not resolved.is_file():
            self._send_json(404, {"error": "image file not found"})
            return

        result = self.classifier.classify(
            resolved,
            candidate_labels=_coerce_candidate_labels(payload.get("candidate_labels")),
            topk=int(payload.get("topk", 3) or 3),
        )
        self._send_json(
            200,
            {
                **result.to_dict(),
                "image_path": str(resolved),
            },
        )

    def _handle_classify_upload(self) -> None:
        form = self._parse_multipart_form()
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "file", None):
            self._send_json(400, {"error": "file is required"})
            return

        raw = file_item.file.read()
        if not raw:
            self._send_json(400, {"error": "uploaded file is empty"})
            return

        uploads_dir = ensure_dir(self.project_root / "artifacts" / "uploads" / "lamp-classifier")
        original_name = Path(getattr(file_item, "filename", "") or "upload.png")
        suffix = original_name.suffix if original_name.suffix else ".png"
        upload_path = uploads_dir / f"{uuid.uuid4().hex}{suffix}"
        upload_path.write_bytes(raw)

        candidate_labels = _coerce_candidate_labels(form.getfirst("candidate_labels", ""))
        topk_value = int(form.getfirst("topk", "3") or 3)
        result = self.classifier.classify(upload_path, candidate_labels=candidate_labels, topk=topk_value)

        self._send_json(
            200,
            {
                **result.to_dict(),
                "upload": {
                    "filename": original_name.name,
                    "stored_path": str(upload_path),
                    "size_bytes": len(raw),
                },
            },
        )

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _parse_multipart_form(self) -> "SimpleMultipartForm":
        content_type = self.headers.get("Content-Type", "")
        marker = "boundary="
        if marker not in content_type:
            raise ValueError("multipart boundary is required")
        boundary = content_type.split(marker, 1)[1].strip().strip('"')
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        return SimpleMultipartForm.parse(boundary=boundary, body=body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class SimpleMultipartFile:
    def __init__(self, filename: str, raw: bytes) -> None:
        self.filename = filename
        self.file = io.BytesIO(raw)


class SimpleMultipartForm(dict[str, Any]):
    @classmethod
    def parse(cls, boundary: str, body: bytes) -> "SimpleMultipartForm":
        instance = cls()
        delimiter = f"--{boundary}".encode("utf-8")
        parts = body.split(delimiter)
        for part in parts:
            chunk = part.strip()
            if not chunk or chunk == b"--":
                continue
            headers_blob, separator, data = chunk.partition(b"\r\n\r\n")
            if not separator:
                continue
            header_lines = headers_blob.decode("utf-8", errors="ignore").split("\r\n")
            disposition = next(
                (line for line in header_lines if line.lower().startswith("content-disposition:")),
                "",
            )
            attrs = {}
            for fragment in disposition.split(";")[1:]:
                if "=" not in fragment:
                    continue
                key, value = fragment.split("=", 1)
                attrs[key.strip()] = value.strip().strip('"')
            name = attrs.get("name", "")
            filename = attrs.get("filename")
            payload = data.rstrip(b"\r\n")
            if not name:
                continue
            instance[name] = SimpleMultipartFile(filename, payload) if filename else payload.decode("utf-8")
        return instance

    def getfirst(self, key: str, default: str = "") -> str:
        value = self.get(key, default)
        if isinstance(value, SimpleMultipartFile):
            return default
        return str(value)


def _coerce_candidate_labels(raw: Any) -> list[str]:
    if raw is None:
        return list(DEFAULT_LAMP_LABELS)
    if isinstance(raw, list):
        labels = [str(item).strip() for item in raw if str(item).strip()]
        return labels or list(DEFAULT_LAMP_LABELS)
    text = str(raw).strip()
    if not text:
        return list(DEFAULT_LAMP_LABELS)
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            labels = [str(item).strip() for item in parsed if str(item).strip()]
            return labels or list(DEFAULT_LAMP_LABELS)
    labels = [item.strip() for item in text.split(",") if item.strip()]
    return labels or list(DEFAULT_LAMP_LABELS)


def build_lamp_type_server(
    host: str = "127.0.0.1",
    port: int = 8090,
    project_root: str | Path = ".",
    model_id: str | None = None,
    candidate_labels: list[str] | None = None,
) -> ThreadingHTTPServer:
    LampTypeApiHandler.project_root = Path(project_root).resolve()
    LampTypeApiHandler.classifier = OpenSourceLampTypeClassifier(
        model_id=model_id or "openai/clip-vit-base-patch32",
        candidate_labels=candidate_labels or list(DEFAULT_LAMP_LABELS),
    )
    return ThreadingHTTPServer((host, port), LampTypeApiHandler)


def serve_lamp_type_api(
    host: str = "127.0.0.1",
    port: int = 8090,
    project_root: str | Path = ".",
    model_id: str | None = None,
    candidate_labels: list[str] | None = None,
) -> None:
    server = build_lamp_type_server(
        host=host,
        port=port,
        project_root=project_root,
        model_id=model_id,
        candidate_labels=candidate_labels,
    )
    print(f"Serving lamp type API at http://{host}:{port}")
    server.serve_forever()
