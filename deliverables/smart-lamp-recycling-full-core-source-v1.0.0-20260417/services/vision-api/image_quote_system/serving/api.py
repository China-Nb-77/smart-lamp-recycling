from __future__ import annotations

import io
import json
import mimetypes
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..classification import DEFAULT_LAMP_LABELS, enrich_quote_payload_with_lamp_type, get_default_lamp_type_classifier
from ..config import load_config
from ..io_utils import ensure_dir
from ..recommend_api import LampRecommendService
from .agent_backend import AgentBackend


FOLLOW_UP_QUESTIONS = [
    {
        "id": "install_type",
        "question": "你更想换成哪种类型？",
        "options": [
            {"value": "pendant", "label": "吊灯"},
            {"value": "wall", "label": "壁灯"},
            {"value": "floor", "label": "落地灯"},
            {"value": "any", "label": "都可以"},
        ],
    },
    {
        "id": "budget_level",
        "question": "预算更偏哪一档？",
        "options": [
            {"value": "economy", "label": "省钱优先"},
            {"value": "balanced", "label": "均衡"},
            {"value": "premium", "label": "升级款"},
        ],
    },
    {
        "id": "material",
        "question": "你偏好的材质是什么？",
        "options": [
            {"value": "aluminum", "label": "铝"},
            {"value": "glass", "label": "玻璃"},
            {"value": "brass", "label": "铜"},
            {"value": "any", "label": "无所谓"},
        ],
    },
]


class QuoteApiHandler(BaseHTTPRequestHandler):
    config_dir = "configs"
    agent_backend = AgentBackend()
    lamp_type_classifier = get_default_lamp_type_classifier()
    recommend_service = LampRecommendService()

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json(200, {"status": "ok"})
                return
            if parsed.path == "/catalog-image":
                self._handle_catalog_image(parsed.query)
                return
            if parsed.path.startswith("/agent/"):
                self._handle_agent_get(parsed)
                return
            self._send_json(404, {"error": "not found"})
        except Exception as exc:  # pragma: no cover
            self._send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path in {"/classify", "/classify-lamp"}:
                self._handle_classify_lamp_by_path()
                return
            if parsed.path in {"/classify-upload", "/classify-lamp-upload"}:
                self._handle_classify_lamp_upload()
                return
            if parsed.path == "/api/recommend":
                self._handle_recommend_lamps()
                return
            if self.path == "/quote":
                self._handle_quote_by_path()
                return
            if self.path == "/quote-upload":
                self._handle_quote_upload()
                return
            if self.path == "/recommend":
                self._handle_recommend()
                return
            if parsed.path.startswith("/agent/"):
                self._handle_agent_post(parsed)
                return
            self._send_json(404, {"error": "not found"})
        except Exception as exc:  # pragma: no cover
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_quote_by_path(self) -> None:
        payload = self._read_json_body()
        image_path = payload.get("image_path")
        if not image_path:
            self._send_json(400, {"error": "image_path is required"})
            return

        config = load_config(self.config_dir)
        project_root = Path(config["project"]["root_dir"])
        resolved_image_path = Path(image_path)
        if not resolved_image_path.is_absolute():
            resolved_image_path = (project_root / resolved_image_path).resolve()
        if self.agent_backend.backend_mode == "mock":
            self._send_json(200, self.agent_backend._identify_and_quote(resolved_image_path, self.config_dir))
            return

        from ..pipeline import quote_single_image

        result = quote_single_image(resolved_image_path, config_dir=self.config_dir, topk=payload.get("topk"))
        self._send_json(200, _build_quote_payload(result))

    def _handle_classify_lamp_by_path(self) -> None:
        payload = self._read_json_body()
        image_path = str(payload.get("image_path", "")).strip()
        if not image_path:
            self._send_json(400, {"error": "image_path is required"})
            return

        config = load_config(self.config_dir)
        project_root = Path(config["project"]["root_dir"]).resolve()
        resolved_image_path = Path(image_path)
        if not resolved_image_path.is_absolute():
            resolved_image_path = (project_root / resolved_image_path).resolve()
        if not resolved_image_path.is_file():
            self._send_json(404, {"error": "image file not found"})
            return

        result = self.lamp_type_classifier.classify(
            resolved_image_path,
            candidate_labels=_coerce_candidate_labels(payload.get("candidate_labels")),
            topk=int(payload.get("topk", 3) or 3),
        )
        self._send_json(
            200,
            {
                "success": True,
                "lamp_type": result.label,
                "confidence": round(float(result.score), 6),
                **result.to_dict(),
                "image_path": str(resolved_image_path),
            },
        )

    def _handle_classify_lamp_upload(self) -> None:
        form = self._parse_multipart_form()
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "file", None):
            self._send_json(400, {"error": "file is required"})
            return

        config = load_config(self.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        upload_dir = ensure_dir(root / "artifacts" / "uploads" / "lamp-classifier")
        original_name = Path(getattr(file_item, "filename", "") or "upload.png")
        suffix = original_name.suffix if original_name.suffix else ".png"
        upload_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        raw = file_item.file.read()
        if not raw:
            self._send_json(400, {"error": "uploaded file is empty"})
            return
        upload_path.write_bytes(raw)

        result = self.lamp_type_classifier.classify(
            upload_path,
            candidate_labels=_coerce_candidate_labels(form.getfirst("candidate_labels", "")),
            topk=int(form.getfirst("topk", "3") or 3),
        )
        self._send_json(
            200,
            {
                "success": True,
                "lamp_type": result.label,
                "confidence": round(float(result.score), 6),
                **result.to_dict(),
                "upload": {
                    "filename": original_name.name,
                    "stored_path": str(upload_path.resolve()),
                    "size_bytes": len(raw),
                },
            },
        )

    def _handle_quote_upload(self) -> None:
        form = self._parse_multipart_form()
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "file", None):
            self._send_json(400, {"error": "file is required"})
            return

        config = load_config(self.config_dir)
        root = Path(config["project"]["root_dir"]).resolve()
        upload_dir = ensure_dir(root / "artifacts" / "uploads" / "vision-api")
        original_name = Path(getattr(file_item, "filename", "") or "upload.png")
        suffix = original_name.suffix if original_name.suffix else ".png"
        upload_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
        raw = file_item.file.read()
        if not raw:
            self._send_json(400, {"error": "uploaded file is empty"})
            return
        upload_path.write_bytes(raw)

        topk_raw = form.getfirst("topk", "")
        topk_value = int(topk_raw) if str(topk_raw).strip() else None
        if self.agent_backend.backend_mode == "mock":
            payload = self.agent_backend._identify_and_quote(upload_path, self.config_dir)
        else:
            from ..pipeline import quote_single_image

            result = quote_single_image(upload_path, config_dir=self.config_dir, topk=topk_value)
            payload = _build_quote_payload(result)
        payload["upload"] = {
            "filename": original_name.name,
            "stored_path": str(upload_path.resolve()),
            "size_bytes": len(raw),
        }
        self._send_json(200, payload)

    def _handle_recommend_lamps(self) -> None:
        payload = self._read_json_body()
        user_input = str(payload.get("user_input", "")).strip()
        if not user_input:
            self._send_json(400, {"error": True, "message": "user_input is required"})
            return
        limit = int(payload.get("limit", 3) or 3)
        try:
            result = self.recommend_service.recommend(user_input, limit=limit)
        except Exception as exc:
            self._send_json(502, {"error": True, "message": str(exc)})
            return
        self._send_json(200, result)

    def _handle_recommend(self) -> None:
        payload = self._read_json_body()
        reference_sku_id = str(payload.get("reference_sku_id", "")).strip()
        if not reference_sku_id:
            self._send_json(400, {"error": "reference_sku_id is required"})
            return

        preferences = payload.get("preferences")
        if preferences is not None and not isinstance(preferences, dict):
            self._send_json(400, {"error": "preferences must be an object"})
            return
        limit = int(payload.get("limit", 3) or 3)
        if self.agent_backend.backend_mode == "mock":
            session = self.agent_backend.ensure_session("preview-session")
            session.quote_payload = {
                "summary": {
                    "matched_sku_id": reference_sku_id,
                    "matched_title": reference_sku_id,
                    "recycle_quote": 0.0,
                    "currency": "CNY",
                }
            }
            session.preferences = {
                "install_type": str((preferences or {}).get("install_type", "any")),
                "budget_level": str((preferences or {}).get("budget_level", "balanced")),
                "space": "living_room",
            }
            result = self.agent_backend._build_recommendations(session, self.config_dir)
        else:
            from ..recommendation import recommend_replacement_lamps

            result = recommend_replacement_lamps(
                reference_sku_id=reference_sku_id,
                preferences=preferences or {},
                config_dir=self.config_dir,
                limit=limit,
            )
        self._send_json(200, result)

    def _handle_catalog_image(self, query_string: str) -> None:
        query = parse_qs(query_string)
        raw_path = (query.get("path") or [""])[0].strip()
        if not raw_path:
            self._send_json(400, {"error": "path is required"})
            return

        resolved_path = _resolve_project_path(self.config_dir, raw_path)
        if not resolved_path.is_file():
            self._send_json(404, {"error": "image not found"})
            return

        project_root = _project_root(self.config_dir)
        try:
            resolved_path.relative_to(project_root)
        except ValueError as exc:
            raise ValueError("path is outside project root") from exc

        mime_type = mimetypes.guess_type(resolved_path.name)[0] or "application/octet-stream"
        raw = resolved_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(raw)

    def _handle_agent_get(self, parsed) -> None:
        query = parse_qs(parsed.query)
        if parsed.path == "/agent/forms/checkout":
            session_id = (query.get("session_id") or [""])[0].strip()
            if not session_id:
                self._send_json(400, {"error": "session_id is required"})
                return
            payload = self.agent_backend.get_checkout_form(session_id)
            self._send_json(200, payload)
            return

        segments = [part for part in parsed.path.split("/") if part]
        if len(segments) >= 3 and segments[1] == "orders":
            order_id = segments[2]
            if len(segments) == 3:
                sync = (query.get("sync") or ["true"])[0].lower() != "false"
                self._send_json(200, self.agent_backend.get_order(order_id, sync=sync))
                return
            if len(segments) == 4 and segments[3] == "electronic":
                qr_token = (query.get("qrToken") or [""])[0].strip()
                if not qr_token:
                    self._send_json(400, {"error": "qrToken is required"})
                    return
                self._send_json(200, self.agent_backend.get_electronic_order(order_id, qr_token))
                return
            if len(segments) == 4 and segments[3] == "logistics":
                self._send_json(200, self.agent_backend.get_logistics(order_id))
                return
            if len(segments) == 4 and segments[3] == "logistics-map":
                self._send_json(200, self.agent_backend.get_logistics_map(order_id))
                return

        self._send_json(404, {"error": "not found"})

    def _handle_agent_post(self, parsed) -> None:
        if parsed.path == "/agent/sessions":
            payload = self._read_json_body()
            requested_session_id = str(payload.get("session_id", "")).strip() or None
            self._send_json(200, self.agent_backend.create_session(requested_session_id))
            return
        if parsed.path == "/agent/addresses/normalize":
            self._send_json(200, self.agent_backend.normalize_address(self._read_json_body()))
            return
        if parsed.path == "/agent/addresses/locate":
            self._send_json(200, self.agent_backend.locate_address(self._read_json_body()))
            return
        if parsed.path == "/agent/orders":
            self._send_json(200, self.agent_backend.create_order(self._read_json_body()))
            return

        segments = [part for part in parsed.path.split("/") if part]
        if len(segments) >= 3 and segments[1] == "sessions":
            session_id = segments[2]
            if len(segments) == 4 and segments[3] == "image":
                form = self._parse_multipart_form()
                file_item = form["file"] if "file" in form else None
                if file_item is None or not getattr(file_item, "file", None):
                    self._send_json(400, {"error": "file is required"})
                    return
                raw = file_item.file.read()
                filename = getattr(file_item, "filename", "") or "upload.png"
                self._send_json(
                    200,
                    self.agent_backend.upload_old_lamp(session_id, raw, filename, self.config_dir),
                )
                return
            if len(segments) == 4 and segments[3] == "messages":
                payload = self._read_json_body()
                text = str(payload.get("text", "")).strip()
                if not text:
                    self._send_json(400, {"error": "text is required"})
                    return
                self._send_json(
                    200,
                    self.agent_backend.handle_user_message(session_id, text, self.config_dir),
                )
                return
            if len(segments) == 4 and segments[3] == "preferences":
                self._send_json(
                    200,
                    self.agent_backend.submit_preferences(
                        session_id,
                        self._read_json_body(),
                        self.config_dir,
                    ),
                )
                return
            if len(segments) == 5 and segments[3] == "recommendations" and segments[4] == "select":
                payload = self._read_json_body()
                sku_id = str(payload.get("sku_id", "")).strip()
                if not sku_id:
                    self._send_json(400, {"error": "sku_id is required"})
                    return
                self._send_json(200, self.agent_backend.select_recommendation(session_id, sku_id))
                return

        if len(segments) >= 3 and segments[1] == "orders":
            order_id = segments[2]
            if len(segments) == 4 and segments[3] == "qr":
                payload = self._read_json_body()
                app_origin = self.headers.get("Origin") or f"http://{self.headers.get('Host', 'localhost:5173')}"
                self._send_json(200, self.agent_backend.create_qr(order_id, payload, app_origin))
                return

        self._send_json(404, {"error": "not found"})

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


def build_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    config_dir: str | Path = "configs",
) -> ThreadingHTTPServer:
    QuoteApiHandler.config_dir = str(Path(config_dir).resolve())
    return ThreadingHTTPServer((host, port), QuoteApiHandler)


def serve_api(host: str = "127.0.0.1", port: int = 8000, config_dir: str | Path = "configs") -> None:
    server = build_server(host=host, port=port, config_dir=config_dir)
    print(f"Serving image quote API at http://{host}:{port}")
    server.serve_forever()


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


def _project_root(config_dir: str | Path) -> Path:
    config = load_config(config_dir)
    return Path(config["project"]["root_dir"]).resolve()


def _resolve_project_path(config_dir: str | Path, raw_path: str) -> Path:
    project_root = _project_root(config_dir)
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def _build_quote_payload(result) -> dict[str, Any]:
    payload = result.to_dict()
    first_line_item = payload["line_items"][0] if payload.get("line_items") else None
    response = {
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
    image_path = payload.get("image_path")
    if image_path:
        response = enrich_quote_payload_with_lamp_type(response, image_path)
    return response


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
