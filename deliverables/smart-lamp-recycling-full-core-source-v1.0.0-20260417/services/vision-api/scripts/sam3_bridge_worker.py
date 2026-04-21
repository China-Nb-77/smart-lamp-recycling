from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(Path.cwd().resolve()) not in sys.path:
    sys.path.insert(0, str(Path.cwd().resolve()))

from image_quote_system.annotation.sam3_checkpoint import build_sam3_image_model_runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--model-cfg", default="")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    try:
        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on external runtime
        raise RuntimeError("sam3 package is not installed in the bridge runtime") from exc

    model = build_sam3_image_model_runtime(
        build_sam3_image_model,
        checkpoint_path=args.checkpoint,
        model_cfg=args.model_cfg,
        device=args.device,
    )
    processor = Sam3Processor(model)
    image = Image.open(args.image).convert("RGB")
    state = processor.set_image(image)
    output = processor.set_text_prompt(state=state, prompt=args.prompt)

    scores = output["scores"]
    if hasattr(scores, "detach"):
        scores = scores.detach().cpu().numpy()
    scores = np.asarray(scores)
    if scores.size == 0:
        raise RuntimeError("sam3 bridge returned no instances for the provided prompt")
    best_idx = int(np.argmax(scores))

    mask = output["masks"][best_idx]
    if hasattr(mask, "detach"):
        mask = mask.detach().cpu().numpy()
    mask = np.asarray(mask)
    if mask.ndim > 2:
        mask = np.squeeze(mask)
    mask = (mask > 0).astype("uint8")

    box = output["boxes"][best_idx]
    if hasattr(box, "detach"):
        box = box.detach().cpu().numpy()
    box = np.asarray(box).tolist()

    payload = {
        "width": image.size[0],
        "height": image.size[1],
        "bbox_xyxy": [int(round(value)) for value in box],
        "score": float(scores[best_idx]),
        "mask": mask.tolist(),
    }
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
