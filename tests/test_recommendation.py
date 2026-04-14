from __future__ import annotations

import unittest
from pathlib import Path

from image_quote_system.recommendation import recommend_replacement_lamps


class RecommendationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def test_recommend_replacement_lamps_returns_ranked_candidates(self) -> None:
        result = recommend_replacement_lamps(
            reference_sku_id="SKU-ALU-PENDANT-S",
            preferences={
                "install_type": "wall",
                "budget_level": "premium",
                "material": "brass",
            },
            config_dir=self.repo_root / "configs",
            limit=2,
        )

        self.assertEqual(result["reference"]["sku_id"], "SKU-ALU-PENDANT-S")
        self.assertEqual(len(result["recommendations"]), 2)
        self.assertNotEqual(
            result["recommendations"][0]["sku_id"],
            "SKU-ALU-PENDANT-S",
        )
        self.assertGreaterEqual(
            result["recommendations"][0]["fit_score"],
            result["recommendations"][1]["fit_score"],
        )


if __name__ == "__main__":
    unittest.main()
