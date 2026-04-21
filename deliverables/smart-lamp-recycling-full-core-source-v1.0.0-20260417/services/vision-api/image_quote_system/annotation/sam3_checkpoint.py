from __future__ import annotations

import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any


CHECKPOINT_ARG_ALIASES = ("checkpoint", "checkpoint_path", "ckpt_path")
MODEL_CFG_ARG_ALIASES = ("model_cfg", "config_path", "model_config")


def build_sam3_image_model_runtime(
    build_sam3_image_model,
    *,
    checkpoint_path: str = "",
    model_cfg: str = "",
    device: str = "cuda",
):
    """
    Build a SAM3 image model while supporting community safetensors checkpoints.

    Some SAM3 builds accept `checkpoint_path` directly, but community mirrors often
    ship `.safetensors`, which the upstream builder does not load via `torch.load`.
    """

    signature = inspect.signature(build_sam3_image_model)
    kwargs: dict[str, Any] = {}

    if model_cfg:
        _apply_supported_kwarg(signature, kwargs, MODEL_CFG_ARG_ALIASES, model_cfg)
    if device:
        _apply_supported_kwarg(signature, kwargs, ("device",), device)

    resolved_checkpoint = str(Path(checkpoint_path).resolve()) if checkpoint_path else ""
    if resolved_checkpoint and not Path(resolved_checkpoint).exists():
        raise FileNotFoundError(f"SAM3 checkpoint not found: {resolved_checkpoint}")
    checkpoint_alias = _find_supported_alias(signature, CHECKPOINT_ARG_ALIASES)
    requires_manual_load = bool(resolved_checkpoint) and (
        _is_safetensors_path(resolved_checkpoint) or checkpoint_alias is None
    )

    if resolved_checkpoint and checkpoint_alias and not requires_manual_load:
        kwargs[checkpoint_alias] = resolved_checkpoint
    elif resolved_checkpoint and "load_from_HF" in signature.parameters:
        kwargs["load_from_HF"] = False

    model = build_sam3_image_model(**kwargs)
    if resolved_checkpoint and requires_manual_load:
        load_sam3_image_checkpoint(model, resolved_checkpoint)
    return model


def load_sam3_image_checkpoint(model, checkpoint_path: str | Path) -> dict[str, Any]:
    path = Path(checkpoint_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"SAM3 checkpoint not found: {path}")

    raw_state_dict = _load_raw_state_dict(path)
    mapped_state_dict, strategy, matched_key_count = remap_sam3_image_state_dict(model, raw_state_dict)
    if matched_key_count <= 0:
        raise RuntimeError(
            "SAM3 checkpoint keys are incompatible with the current image model: "
            f"{path.name}"
        )

    missing_keys, unexpected_keys = model.load_state_dict(mapped_state_dict, strict=False)
    return {
        "checkpoint_path": str(path),
        "strategy": strategy,
        "matched_key_count": matched_key_count,
        "missing_keys": list(missing_keys),
        "unexpected_keys": list(unexpected_keys),
    }


def remap_sam3_image_state_dict(model, state_dict: Mapping[str, Any]) -> tuple[dict[str, Any], str, int]:
    expected_keys = set(model.state_dict().keys())
    has_inst_interactive_predictor = getattr(model, "inst_interactive_predictor", None) is not None
    best_candidate: dict[str, Any] = {}
    best_strategy = "identity"
    best_overlap = -1

    for strategy, candidate in _candidate_state_dicts(dict(state_dict), has_inst_interactive_predictor):
        overlap = sum(1 for key in candidate if key in expected_keys)
        if overlap > best_overlap:
            best_candidate = candidate
            best_strategy = strategy
            best_overlap = overlap

    return best_candidate, best_strategy, best_overlap


def _candidate_state_dicts(
    state_dict: dict[str, Any],
    has_inst_interactive_predictor: bool,
) -> list[tuple[str, dict[str, Any]]]:
    candidates: list[tuple[str, dict[str, Any]]] = []
    base_variants = [
        ("identity", state_dict),
        ("strip model.", _strip_prefix(state_dict, "model.")),
        ("strip module.", _strip_prefix(state_dict, "module.")),
        ("strip module.model.", _strip_prefix(_strip_prefix(state_dict, "module."), "model.")),
        ("strip state_dict.", _strip_prefix(state_dict, "state_dict.")),
    ]

    for base_name, base_variant in base_variants:
        candidates.append((base_name, base_variant))

        detector_variant = _strip_detector_and_tracker_prefixes(
            base_variant,
            has_inst_interactive_predictor=has_inst_interactive_predictor,
        )
        if detector_variant:
            candidates.append((f"{base_name} + detector/tracker", detector_variant))

        oss_variant = _strip_oss_demo_prefixes(
            base_variant,
            has_inst_interactive_predictor=has_inst_interactive_predictor,
        )
        if oss_variant:
            candidates.append((f"{base_name} + sam3_model/sam2_predictor", oss_variant))

    return candidates


def _strip_detector_and_tracker_prefixes(
    state_dict: Mapping[str, Any],
    *,
    has_inst_interactive_predictor: bool,
) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for key, value in state_dict.items():
        if key.startswith("detector."):
            mapped[key[len("detector.") :]] = value
        elif has_inst_interactive_predictor and key.startswith("tracker."):
            suffix = key[len("tracker.") :]
            mapped[f"inst_interactive_predictor.model.{suffix}"] = value
    return mapped


def _strip_oss_demo_prefixes(
    state_dict: Mapping[str, Any],
    *,
    has_inst_interactive_predictor: bool,
) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for key, value in state_dict.items():
        if key.startswith("sam3_model."):
            mapped[key[len("sam3_model.") :]] = value
        elif has_inst_interactive_predictor and key.startswith("sam2_predictor."):
            suffix = key[len("sam2_predictor.") :]
            mapped[f"inst_interactive_predictor.model.{suffix}"] = value
    return mapped


def _strip_prefix(state_dict: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        key[len(prefix) :] if key.startswith(prefix) else key: value
        for key, value in state_dict.items()
    }


def _load_raw_state_dict(path: Path) -> dict[str, Any]:
    if _is_safetensors_path(path):
        return _load_safetensors_state_dict(path)
    return _load_torch_state_dict(path)


def _load_torch_state_dict(path: Path) -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - depends on runtime
        raise RuntimeError("torch is required to load SAM3 checkpoints") from exc

    checkpoint = torch.load(str(path), map_location="cpu", weights_only=True)
    return _unwrap_container_mappings(checkpoint, path)


def _load_safetensors_state_dict(path: Path) -> dict[str, Any]:
    try:
        from safetensors.torch import load_file
    except ImportError as exc:  # pragma: no cover - depends on runtime
        raise RuntimeError(
            "safetensors is required to load community SAM3 checkpoints; "
            "install it in the active runtime"
        ) from exc

    checkpoint = load_file(str(path), device="cpu")
    return _unwrap_container_mappings(checkpoint, path)


def _unwrap_container_mappings(checkpoint: Any, path: Path) -> dict[str, Any]:
    if not isinstance(checkpoint, Mapping):
        raise RuntimeError(f"SAM3 checkpoint does not contain a state dict: {path}")

    current = dict(checkpoint)
    while True:
        nested = current.get("model") or current.get("state_dict")
        if isinstance(nested, Mapping):
            current = dict(nested)
            continue
        break
    return current


def _apply_supported_kwarg(
    signature: inspect.Signature,
    kwargs: dict[str, Any],
    aliases: tuple[str, ...],
    value: Any,
) -> None:
    alias = _find_supported_alias(signature, aliases)
    if alias:
        kwargs[alias] = value


def _find_supported_alias(signature: inspect.Signature, aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        if alias in signature.parameters:
            return alias
    return ""


def _is_safetensors_path(path: str | Path) -> bool:
    return str(path).lower().endswith(".safetensors")
