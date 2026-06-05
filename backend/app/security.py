from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from .errors import UnauthorizedError


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


@dataclass(slots=True)
class SessionTokenPayload:
    session_id: str
    user_id: str
    client_session_id: str | None
    exp: int


class SessionTokenManager:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode("utf-8")

    def issue(
        self,
        *,
        session_id: str,
        user_id: str,
        client_session_id: str | None,
        expires_at_epoch: int,
    ) -> str:
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "client_session_id": client_session_id,
            "exp": expires_at_epoch,
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(self._secret, raw, hashlib.sha256).digest()
        return f"{_b64encode(raw)}.{_b64encode(signature)}"

    def verify(self, token: str) -> SessionTokenPayload:
        parts = token.split(".", 1)
        if len(parts) != 2:
            raise UnauthorizedError("invalid session token")
        raw_payload, raw_signature = parts
        payload_bytes = _b64decode(raw_payload)
        signature = _b64decode(raw_signature)
        expected = hmac.new(self._secret, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise UnauthorizedError("invalid session token")
        payload = json.loads(payload_bytes.decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp <= int(time.time()):
            raise UnauthorizedError("session token expired")
        return SessionTokenPayload(
            session_id=str(payload.get("session_id", "")).strip(),
            user_id=str(payload.get("user_id", "")).strip(),
            client_session_id=str(payload.get("client_session_id") or "").strip() or None,
            exp=exp,
        )

