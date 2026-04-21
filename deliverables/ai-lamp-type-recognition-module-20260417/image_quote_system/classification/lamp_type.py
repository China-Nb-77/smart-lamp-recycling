from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_LAMP_LABELS = [
    "chandelier",
    "ceiling lamp",
    "pendant light",
    "table lamp",
    "desk lamp",
    "floor lamp",
    "wall lamp",
    "spotlight",
]


@dataclass(slots=True)
class LampTypeClassificationResult:
    label: str
    score: float
    candidates: list[dict[str, Any]]
    model_id: str
    backend: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "score": round(float(self.score), 6),
            "candidates": [
                {
                    "label": str(item.get("label", "")),
                    "score": round(float(item.get("score", 0.0)), 6),
                }
                for item in self.candidates
            ],
            "model_id": self.model_id,
            "backend": self.backend,
        }


class OpenSourceLampTypeClassifier:
    """Lamp type classifier using an open-source Hugging Face zero-shot model.

    This implements the AGENTS.md requirement with a CPU-friendly, no-training
    inference path. If a dedicated lamp checkpoint is not available at runtime,
    this classifier uses a community model and candidate lamp labels directly.
    """

    def __init__(
        self,
        *,
        model_id: str = "openai/clip-vit-base-patch32",
        candidate_labels: list[str] | None = None,
        device: int = -1,
        pipeline_factory: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self.candidate_labels = candidate_labels or list(DEFAULT_LAMP_LABELS)
        self.device = device
        self._pipeline_factory = pipeline_factory
        self._pipeline = None

    @property
    def backend(self) -> str:
        return "huggingface-transformers-zero-shot"

    def classify(
        self,
        image: str | Path | Image.Image,
        *,
        candidate_labels: list[str] | None = None,
        topk: int = 3,
    ) -> LampTypeClassificationResult:
        labels = candidate_labels or self.candidate_labels
        if not labels:
            raise ValueError("candidate_labels must not be empty")

        pipeline = self._load_pipeline()
        image_input = image if isinstance(image, Image.Image) else Image.open(image).convert("RGB")
        raw = pipeline(image_input, candidate_labels=labels)

        normalized = self._normalize_predictions(raw)
        normalized = normalized[: max(int(topk), 1)]
        if not normalized:
            raise RuntimeError("classifier returned no predictions")

        best = normalized[0]
        return LampTypeClassificationResult(
            label=str(best["label"]),
            score=float(best["score"]),
            candidates=normalized,
            model_id=self.model_id,
            backend=self.backend,
        )

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        pipeline_factory = self._pipeline_factory
        if pipeline_factory is None:
            try:
                from transformers import pipeline as hf_pipeline
            except ImportError as exc:  # pragma: no cover - exercised in runtime env
                raise RuntimeError(
                    "transformers is required for lamp type classification. "
                    "Install with: pip install transformers torch"
                ) from exc
            pipeline_factory = hf_pipeline

        self._pipeline = pipeline_factory(
            task="zero-shot-image-classification",
            model=self.model_id,
            device=self.device,
        )
        return self._pipeline

    def _normalize_predictions(self, raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            raise RuntimeError(f"unexpected classifier output type: {type(raw)!r}")

        predictions: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            predictions.append(
                {
                    "label": label,
                    "score": float(item.get("score", 0.0)),
                }
            )
        predictions.sort(key=lambda item: item["score"], reverse=True)
        return predictions


@lru_cache(maxsize=2)
def get_default_lamp_type_classifier(
    model_id: str = "openai/clip-vit-base-patch32",
) -> OpenSourceLampTypeClassifier:
    return OpenSourceLampTypeClassifier(model_id=model_id)


def normalize_lamp_type_key(label: str) -> str:
    lowered = str(label or "").strip().lower()
    if not lowered:
        return "any"
    if "wall" in lowered:
        return "wall"
    if "floor" in lowered:
        return "floor"
    if "chandelier" in lowered or "pendant" in lowered:
        return "pendant"
    if "ceiling" in lowered or "desk" in lowered or "table" in lowered or "spot" in lowered:
        return "any"
    return "any"


def enrich_quote_payload_with_lamp_type(
    payload: dict[str, Any],
    image: str | Path | Image.Image,
    *,
    topk: int = 3,
    classifier: OpenSourceLampTypeClassifier | None = None,
) -> dict[str, Any]:
    """Best-effort classification enrichment for existing quote payloads.

    Failures are swallowed so the current quote/recommendation flow keeps
    working even if the open-source model dependencies are not installed.
    """

    summary = payload.setdefault("summary", {})
    try:
        result = (classifier or get_default_lamp_type_classifier()).classify(image, topk=topk)
    except Exception:
        return payload

    summary["lamp_type_label"] = result.label
    summary["lamp_type_score"] = round(float(result.score), 6)
    summary["lamp_type_backend"] = result.backend
    summary["lamp_type_model_id"] = result.model_id
    summary["recognized_type"] = normalize_lamp_type_key(result.label)
    return payload
