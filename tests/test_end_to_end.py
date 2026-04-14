from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from image_quote_system.baseline import evaluate_baseline
from image_quote_system.annotation.pipeline import export_training_version, generate_review_dashboard, prelabel_directory
from image_quote_system.annotation.sam3_adapter import Sam3Annotator
from image_quote_system.config import load_config
from image_quote_system.data.catalog import load_catalog
from image_quote_system.data.prepare import prepare_data
from image_quote_system.embedding.openclip_embedder import OpenClipEmbedder
from image_quote_system.pipeline import quote_single_image
from image_quote_system.pricing import residual_training
from image_quote_system.retrieval.faiss_index import FaissCatalogIndex


class EndToEndPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        prepare_data(cls.repo_root / "configs")
        cls.config = load_config(cls.repo_root / "configs")
        catalog_rows = load_catalog(cls.repo_root / cls.config["paths"]["catalog_csv"])
        embedder = OpenClipEmbedder(cls.config)
        vectors = [embedder.embed_image(cls.repo_root / row["image_path"]) for row in catalog_rows]
        index = FaissCatalogIndex(
            cls.repo_root / cls.config["retrieval"]["faiss_index_path"],
            cls.repo_root / cls.config["retrieval"]["faiss_meta_path"],
        )
        index.build(vectors, catalog_rows)
        cls.sam3_annotation_dir = cls.repo_root / "artifacts" / "sam3_prelabel_test"
        if cls.sam3_annotation_dir.exists():
            shutil.rmtree(cls.sam3_annotation_dir)
        cls.sam3_prelabel_result = prelabel_directory(
            raw_dir=cls.repo_root / "data" / "raw",
            annotation_dir=cls.sam3_annotation_dir,
            category_name="lamp",
            config=cls.config,
            auto_approve=True,
            reviewer="test-suite",
        )
        cls.residual_train_report = residual_training.train_residual_model(
            config_dir=cls.repo_root / "configs",
            num_boost_round=10,
        )
        cls.baseline_report = evaluate_baseline(
            config_dir=cls.repo_root / "configs",
            report_name="baseline_report_test",
            topk=3,
        )

    def test_quote_pipeline_runs(self) -> None:
        query_image = self.repo_root / "data" / "queries" / "SKU-ALU-PENDANT-S_query.png"
        result = quote_single_image(query_image, config_dir=self.repo_root / "configs", topk=3)
        self.assertGreater(result.total_quote, 0.0)
        self.assertGreaterEqual(len(result.line_items), 1)
        self.assertEqual(result.currency, "CNY")
        self.assertIn("price_summary", result.to_dict())
        self.assertGreaterEqual(len(result.line_items[0].topk_similar_items), 1)
        self.assertGreaterEqual(len(result.line_items[0].applied_rules), 1)

    def test_annotation_audit_dashboard_generation(self) -> None:
        dashboard = generate_review_dashboard(
            annotation_dir=self.repo_root / "data" / "annotations",
            output_dir=self.repo_root / "artifacts" / "annotation_review_test",
            status_filter="all",
            sample_size=2,
            seed=7,
        )
        self.assertEqual(dashboard["record_count"], 2)
        self.assertTrue((self.repo_root / "artifacts" / "annotation_review_test" / "index.html").exists())

    def test_sam3_prelabel_chain_runs_with_placeholder_fallback(self) -> None:
        self.assertEqual(self.sam3_prelabel_result["backend"], "sam3-threshold-placeholder")
        self.assertTrue(self.sam3_prelabel_result["placeholder_backend"])
        self.assertEqual(len(self.sam3_prelabel_result["records"]), 3)
        first_record = json.loads(Path(self.sam3_prelabel_result["records"][0]).read_text(encoding="utf-8"))
        first_object = first_record["objects"][0]
        self.assertEqual(first_object["review_status"], "approved")
        self.assertEqual(first_object["reviewer"], "test-suite")
        self.assertTrue(Path(first_object["mask_path"]).exists())

    def test_baseline_evaluation_chain_runs(self) -> None:
        self.assertGreaterEqual(len(self.baseline_report["cases"]), 3)
        self.assertIn("metrics", self.baseline_report)
        self.assertIn("versions", self.baseline_report)
        self.assertTrue(Path(self.baseline_report["report_json"]).exists())
        self.assertTrue(Path(self.baseline_report["report_markdown"]).exists())
        self.assertTrue(Path(self.baseline_report["report_dir"]).exists())
        self.assertIn("detail_artifacts", self.baseline_report)
        self.assertTrue(Path(self.baseline_report["detail_artifacts"]["detection_csv"]).exists())
        self.assertTrue(Path(self.baseline_report["detail_artifacts"]["retrieval_csv"]).exists())
        self.assertTrue(Path(self.baseline_report["detail_artifacts"]["quote_csv"]).exists())
        self.assertTrue(Path(self.baseline_report["detail_artifacts"]["sample_report_markdown"]).exists())
        self.assertGreater(self.baseline_report["metrics"]["retrieval"]["top1_accuracy"], 0.0)

    def test_residual_training_chain_runs(self) -> None:
        if residual_training.HAS_LIGHTGBM:
            self.assertEqual(self.residual_train_report["status"], "ok")
            self.assertTrue(Path(self.residual_train_report["model_path"]).exists())
            self.assertTrue(Path(self.residual_train_report["model_meta_path"]).exists())
            self.assertGreaterEqual(self.residual_train_report["train_case_count"], 1)
            self.assertIn("rule_only_mae", self.residual_train_report["metrics"])
            return

        self.assertEqual(self.residual_train_report["status"], "placeholder")
        self.assertEqual(self.residual_train_report["reason"], "lightgbm not installed")

    def test_residual_training_degrades_when_lightgbm_missing(self) -> None:
        with patch.object(residual_training, "HAS_LIGHTGBM", False):
            report = residual_training.train_residual_model(config_dir=self.repo_root / "configs")
        self.assertEqual(report["status"], "placeholder")
        self.assertEqual(report["reason"], "lightgbm not installed")

    def test_export_training_version_records_dataset_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            annotation_dir = temp_root / "annotations"
            shutil.copytree(self.repo_root / "data" / "annotations", annotation_dir)
            dataset_dir = temp_root / "detection_dataset"
            exports_dir = temp_root / "annotation_exports"
            version_root = temp_root / "dataset_versions"
            decision_file = temp_root / "review_decisions.json"
            first_annotation = sorted((annotation_dir / "records").glob("*.json"))[0]
            decision_file.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "annotation_file": str(first_annotation.resolve()),
                                "status": "approved",
                                "note": "promoted to next round",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8-sig",
            )

            export_result = export_training_version(
                annotation_dir=annotation_dir,
                dataset_dir=dataset_dir,
                exports_dir=exports_dir,
                category_name="lamp",
                version_tag="round-smoke",
                version_root=version_root,
                decision_file=decision_file,
                reviewer="qa-smoke",
                note="smoke export",
            )

            manifest = json.loads(Path(export_result["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["version_tag"], "round-smoke")
            self.assertEqual(manifest["annotation_status_counts"]["approved"], 3)
            self.assertTrue(Path(export_result["dataset_snapshot_dir"]).exists())
            self.assertTrue(Path(export_result["exports_snapshot_dir"]).exists())
            self.assertTrue(Path(export_result["status_csv"]).exists())
            self.assertIsNotNone(export_result["review_summary"])


class Sam3BridgeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.config = load_config(cls.repo_root / "configs")

    def test_sam3_bridge_backend_can_be_mocked(self) -> None:
        config = json.loads(json.dumps(self.config))
        config["annotation"]["sam3"]["backend_priority"] = ["bridge", "placeholder"]
        config["annotation"]["sam3"]["bridge"]["python_executable"] = "python"
        config["annotation"]["sam3"]["bridge"]["checkpoint"] = "artifacts/models/mock_sam3.pt"
        config["annotation"]["sam3"]["bridge"]["model_cfg"] = "configs/mock_sam3.yaml"
        config["annotation"]["sam3"]["bridge"]["device"] = "cpu"
        image_path = self.repo_root / "data" / "raw" / "SKU-ALU-PENDANT-S.png"

        def fake_run(command, cwd, check, capture_output, text, timeout):
            output_json = Path(command[command.index("--output-json") + 1])
            payload = {
                "width": 640,
                "height": 640,
                "bbox_xyxy": [32, 48, 420, 560],
                "score": 0.97,
                "mask": [[1, 1], [1, 1]],
            }
            output_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.assertIn("--checkpoint", command)
            self.assertIn("--model-cfg", command)
            self.assertIn("--device", command)
            self.assertEqual(Path(cwd).resolve(), self.repo_root.resolve())
            self.assertGreater(timeout, 0)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with patch("image_quote_system.annotation.sam3_adapter.subprocess.run", side_effect=fake_run):
            annotator = Sam3Annotator(config)
            result = annotator.prelabel(image_path, "lamp")

        self.assertEqual(result["sam3_backend"], "sam3-bridge")
        self.assertFalse(result["is_placeholder_backend"])
        self.assertEqual(result["objects"][0]["bbox_xyxy"], [32, 48, 420, 560])
        self.assertEqual(result["objects"][0]["sam3_score"], 0.97)

    @unittest.skipUnless(
        os.environ.get("SAM3_BRIDGE_PYTHON") and os.environ.get("SAM3_CHECKPOINT") and os.environ.get("SAM3_MODEL_CFG"),
        "real SAM3 bridge runtime is not configured",
    )
    def test_real_sam3_bridge_runtime_smoke(self) -> None:
        config = json.loads(json.dumps(self.config))
        config["annotation"]["sam3"]["backend_priority"] = ["bridge", "placeholder"]
        result = Sam3Annotator(config).prelabel(self.repo_root / "data" / "raw" / "SKU-ALU-PENDANT-S.png", "lamp")
        self.assertEqual(result["sam3_backend"], "sam3-bridge")
        self.assertFalse(result["is_placeholder_backend"])
        self.assertTrue(result["objects"][0]["bbox_xyxy"][2] > result["objects"][0]["bbox_xyxy"][0])


if __name__ == "__main__":
    unittest.main()
