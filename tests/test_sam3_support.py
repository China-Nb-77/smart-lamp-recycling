from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from image_quote_system.annotation.sam3_checkpoint import load_sam3_image_checkpoint, remap_sam3_image_state_dict
from image_quote_system.annotation.sam3_community import build_huggingface_resolve_url, download_community_checkpoint


class _FakeSam3Model:
    def __init__(self) -> None:
        self.loaded_state_dict = None

    def state_dict(self):
        return {
            "backbone.layer.weight": object(),
            "decoder.class_embed.bias": object(),
        }

    def load_state_dict(self, state_dict, strict=False):
        self.loaded_state_dict = dict(state_dict)
        return [], []


class Sam3CheckpointSupportTest(unittest.TestCase):
    def test_remap_prefers_detector_prefixed_keys_for_image_model(self) -> None:
        model = _FakeSam3Model()
        state_dict = {
            "detector.backbone.layer.weight": "backbone-weight",
            "detector.decoder.class_embed.bias": "decoder-bias",
            "tracker.memory.weight": "unused-tracker-weight",
        }

        remapped, strategy, matched_key_count = remap_sam3_image_state_dict(model, state_dict)

        self.assertEqual(strategy, "identity + detector/tracker")
        self.assertEqual(matched_key_count, 2)
        self.assertEqual(remapped["backbone.layer.weight"], "backbone-weight")
        self.assertEqual(remapped["decoder.class_embed.bias"], "decoder-bias")
        self.assertNotIn("tracker.memory.weight", remapped)

    def test_load_safetensors_checkpoint_uses_remapped_state_dict(self) -> None:
        model = _FakeSam3Model()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "sam3.safetensors"
            checkpoint_path.write_bytes(b"placeholder")

            with patch(
                "image_quote_system.annotation.sam3_checkpoint._load_safetensors_state_dict",
                return_value={
                    "detector.backbone.layer.weight": "backbone-weight",
                    "detector.decoder.class_embed.bias": "decoder-bias",
                },
            ):
                result = load_sam3_image_checkpoint(model, checkpoint_path)

        self.assertEqual(result["matched_key_count"], 2)
        self.assertEqual(model.loaded_state_dict["backbone.layer.weight"], "backbone-weight")
        self.assertEqual(model.loaded_state_dict["decoder.class_embed.bias"], "decoder-bias")


class Sam3CommunityDownloadTest(unittest.TestCase):
    def test_build_huggingface_resolve_url(self) -> None:
        self.assertEqual(
            build_huggingface_resolve_url("AEmotionStudio/sam3", "sam3.safetensors"),
            "https://huggingface.co/AEmotionStudio/sam3/resolve/main/sam3.safetensors?download=1",
        )

    def test_download_skips_existing_file_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sam3.safetensors"
            output_path.write_bytes(b"community-checkpoint")

            result = download_community_checkpoint(
                repo_id="AEmotionStudio/sam3",
                filename="sam3.safetensors",
                output_path=output_path,
                force=False,
            )

        self.assertEqual(result["status"], "exists")
        self.assertEqual(result["output_path"], str(output_path.resolve()))
        self.assertGreater(result["size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
