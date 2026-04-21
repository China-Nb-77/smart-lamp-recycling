from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from .config import AppSettings
from .errors import LLMFormatError, ServiceUnavailable


SYSTEM_PROMPT = """You are the lamp replacement agent brain.

You must drive every turn of the conversation.
Do not act like a fixed workflow template.
Do not reuse canned opening lines unless they are truly appropriate.
Address the user's latest message directly, naturally, and specifically.

Output JSON only with this schema:
{
  "reply": "Chinese reply to the user",
  "intent": "chat | collect_pref | recommend | checkout",
  "confidence": 0.85,
  "suggestions": ["optional follow-up suggestion 1", "optional suggestion 2"],
  "slots": {
    "room": "living_room",
    "budget": 1000,
    "budget_level": "balanced",
    "install_type": "pendant",
    "material": "glass",
    "note": "extra user note"
  }
}

Rules:
- reply must be natural Chinese
- intent must be one of chat, collect_pref, recommend, checkout
- confidence must be between 0 and 1
- suggestions is optional; if present, return 0 to 3 short Chinese prompts
- slots should contain only information supported by the user's message and context
- never fake recognition success, recommendation success, or checkout success
- if no image has been uploaded, do not pretend the old lamp has been recognized
- if requires_review=true, do not lead the user into checkout
- if the user is provocative or playful, respond briefly and steer back naturally instead of repeating a stock refusal
"""


def _now_ms() -> int:
    return int(time.time() * 1000)


def _extract_json_block(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise LLMFormatError("empty llm response")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise LLMFormatError("llm response did not contain json")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMFormatError("llm json parse failed") from exc
    if not isinstance(parsed, dict):
        raise LLMFormatError("llm response root must be json object")
    return parsed


def _trim_text(value: Any) -> str:
    return str(value or "").strip()


@dataclass(slots=True)
class LLMDecision:
    reply: str
    intent: str
    confidence: float
    suggestions: list[str]
    slots: dict[str, Any]
    trace: dict[str, Any]


class SiliconFlowAgent:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def call_llm(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not self._settings.siliconflow_api_key:
            raise ServiceUnavailable("siliconflow api key missing")

        payload = {
            "model": self._settings.siliconflow_model,
            "messages": messages,
            "temperature": self._settings.siliconflow_temperature,
            "stream": False,
        }
        request = urllib_request.Request(
            f"{self._settings.siliconflow_base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._settings.siliconflow_api_key}",
                "Content-Type": "application/json",
            },
        )

        raw = ""
        last_error: ServiceUnavailable | None = None
        for attempt in range(2):
            try:
                with urllib_request.urlopen(request, timeout=self._settings.qna_timeout_seconds) as response:  # noqa: S310
                    raw = response.read().decode("utf-8")
                break
            except urllib_error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                last_error = ServiceUnavailable(
                    "siliconflow request failed",
                    details={"status": exc.code, "reason": detail or str(exc), "attempt": attempt + 1},
                )
            except (urllib_error.URLError, TimeoutError, UnicodeDecodeError) as exc:
                last_error = ServiceUnavailable(
                    "siliconflow request failed",
                    details={"reason": str(exc), "attempt": attempt + 1},
                )
                time.sleep(0.8 * (attempt + 1))
        else:
            raise last_error or ServiceUnavailable("siliconflow request failed")

        try:
            payload_obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMFormatError("siliconflow response was not valid json") from exc

        try:
            content = payload_obj["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMFormatError("siliconflow response missing message content") from exc
        return {
            "raw_response": raw,
            "content": str(content or ""),
            "provider_payload": payload_obj,
        }

    def decide(
        self,
        *,
        messages: list[dict[str, str]],
        context: dict[str, Any],
        prompt_version: str,
    ) -> LLMDecision:
        started = _now_ms()
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": "Current business context JSON:\n" + json.dumps(context, ensure_ascii=False)},
            *messages,
        ]
        response_payload = self.call_llm(prompt_messages)
        raw_content = response_payload["content"]
        parsed = _extract_json_block(raw_content)

        reply = _trim_text(parsed.get("reply") or parsed.get("text"))
        intent = _trim_text(parsed.get("intent") or parsed.get("route")).lower()
        confidence = float(parsed.get("confidence") or 0.0)
        suggestions_raw = parsed.get("suggestions")
        suggestions = (
            [str(item).strip() for item in suggestions_raw if str(item).strip()]
            if isinstance(suggestions_raw, list)
            else []
        )[:3]
        slots = parsed.get("slots") if isinstance(parsed.get("slots"), dict) else {}

        if not reply:
            raise LLMFormatError("llm response missing reply")
        if intent not in {"chat", "collect_pref", "recommend", "checkout"}:
            raise LLMFormatError("llm response intent invalid")
        if not 0.0 <= confidence <= 1.0:
            raise LLMFormatError("llm response confidence invalid")

        trace = {
            "model": self._settings.siliconflow_model,
            "prompt": prompt_messages,
            "response": raw_content,
            "latency": _now_ms() - started,
            "provider_response": response_payload["raw_response"],
            "prompt_version": prompt_version,
        }
        return LLMDecision(
            reply=reply,
            intent=intent,
            confidence=confidence,
            suggestions=suggestions,
            slots=slots,
            trace=trace,
        )
