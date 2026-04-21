import unittest

from image_quote_system.recommend_api import LampRecommendService, RecommendIntent


class _FakeIntentParser:
    def parse(self, user_input: str):
        return RecommendIntent(
            room="卧室",
            brightness="柔和",
            budget="低",
            style="简约",
            keyword="卧室 暖光灯 简约 便宜",
        )


class _FakeTaobaoClient:
    def search_items(self, keyword: str, *, max_items: int = 12):
        return [
            {
                "title": "卧室暖光灯 简约款",
                "price": 59.9,
                "image": "https://example.com/1.jpg",
                "link": "https://example.com/item/1",
            },
            {
                "title": "客厅吊灯 轻奢款",
                "price": 399.0,
                "image": "https://example.com/2.jpg",
                "link": "https://example.com/item/2",
            },
            {
                "title": "卧室床头台灯 暖光",
                "price": 79.0,
                "image": "https://example.com/3.jpg",
                "link": "https://example.com/item/3",
            },
            {
                "title": "简约落地灯 卧室阅读",
                "price": 99.0,
                "image": "https://example.com/4.jpg",
                "link": "https://example.com/item/4",
            },
        ]


class RecommendApiTestCase(unittest.TestCase):
    def test_recommend_returns_real_shape(self):
        service = LampRecommendService(
            intent_parser=_FakeIntentParser(),
            taobao_client=_FakeTaobaoClient(),
        )
        payload = service.recommend("卧室温馨一点的灯", limit=3)
        self.assertEqual(payload["intent"]["room"], "卧室")
        self.assertEqual(payload["keyword"], "卧室 暖光灯 简约 便宜")
        self.assertEqual(len(payload["recommendations"]), 3)
        self.assertTrue(all("title" in item and "link" in item for item in payload["recommendations"]))


if __name__ == "__main__":
    unittest.main()
