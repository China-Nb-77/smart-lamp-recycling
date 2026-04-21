from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_TIMEOUT = 30
DEFAULT_TAOBAO_ITEMS = 12


def _extract_json_block(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty siliconflow response")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("unable to locate JSON in siliconflow response")
    return json.loads(match.group(0))


@dataclass(slots=True)
class RecommendIntent:
    room: str
    brightness: str
    budget: str
    style: str
    keyword: str

    def to_dict(self) -> dict[str, str]:
        return {
            "room": self.room,
            "brightness": self.brightness,
            "budget": self.budget,
            "style": self.style,
            "keyword": self.keyword,
        }


class SiliconFlowIntentParser:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("SILICONFLOW_BASE_URL") or "https://api.siliconflow.cn/v1").rstrip("/")
        self.model = model or os.getenv("SILICONFLOW_RECOMMEND_MODEL", "deepseek-ai/DeepSeek-V3")
        self.timeout_seconds = int(timeout_seconds)

    def parse(self, user_input: str) -> RecommendIntent:
        if not self.api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is required")

        prompt = f"""你是一个灯具推荐助手。

请从用户输入中提取以下信息，并返回JSON：

room（客厅/卧室/厨房/其他）
brightness（柔和/明亮/未知）
budget（低/中/高/未知）
style（现代/简约/轻奢/未知）
keyword（淘宝搜索关键词）

要求：
1. 只返回JSON
2. 不要解释
3. keyword必须适合电商搜索

用户输入：
{user_input}
"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json_block(content)
        return RecommendIntent(
            room=str(parsed.get("room", "其他")).strip() or "其他",
            brightness=str(parsed.get("brightness", "未知")).strip() or "未知",
            budget=str(parsed.get("budget", "未知")).strip() or "未知",
            style=str(parsed.get("style", "未知")).strip() or "未知",
            keyword=str(parsed.get("keyword", "")).strip() or str(user_input).strip(),
        )


class TaobaoMarketSpiderClient:
    """Real Taobao product search adapted from the GitHub project:
    https://github.com/zhangjiancong/MarketSpider
    """

    def __init__(
        self,
        *,
        browser: str | None = None,
        headless: bool | None = None,
        binary_location: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.browser = (browser or os.getenv("TAOBAO_BROWSER", "edge")).strip().lower()
        self.headless = (
            headless
            if headless is not None
            else os.getenv("TAOBAO_HEADLESS", "false").strip().lower() == "true"
        )
        self.binary_location = binary_location or os.getenv("TAOBAO_BROWSER_BINARY", "").strip()
        self.timeout_seconds = int(timeout_seconds)

    def search_items(self, keyword: str, *, max_items: int = DEFAULT_TAOBAO_ITEMS) -> list[dict[str, Any]]:
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.edge.options import Options as EdgeOptions
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("selenium is required for Taobao scraping") from exc

        keyword = str(keyword or "").strip()
        if not keyword:
            raise ValueError("keyword is required")

        if self.browser == "chrome":
            options = ChromeOptions()
            options.binary_location = self.binary_location or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1400,2000")
            driver = webdriver.Chrome(options=options)
        else:
            options = EdgeOptions()
            options.binary_location = self.binary_location or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1400,2000")
            driver = webdriver.Edge(options=options)

        url = f"https://s.taobao.com/search?q={quote(keyword)}"
        try:
            driver.get(url)
            time.sleep(8)
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            except Exception:
                pass
            time.sleep(3)

            items = driver.find_elements(By.CSS_SELECTOR, "#content_items_wrapper>div")
            results: list[dict[str, Any]] = []
            for item in items:
                parsed = self._parse_item(item)
                if not parsed:
                    continue
                results.append(parsed)
                if len(results) >= max_items:
                    break
            if not results:
                raise RuntimeError("no taobao items parsed from page")
            return results
        finally:
            driver.quit()

    def _parse_item(self, item: Any) -> dict[str, Any] | None:
        from selenium.webdriver.common.by import By

        def css_text(selector: str) -> str:
            try:
                return item.find_element(By.CSS_SELECTOR, selector).text.strip()
            except Exception:
                return ""

        def css_attr(selector: str, attr: str) -> str:
            try:
                value = item.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
                return str(value or "").strip()
            except Exception:
                return ""

        title = (
            css_text("a div span")
            or css_text("a")
            or css_text("div")
        )
        title = re.sub(r"\s+", " ", title).strip()
        if not _looks_like_lamp_title(title):
            return None

        link = css_attr("a", "href")
        image = css_attr("img", "src")
        price_text = (
            css_text("a div div div.innerPriceWrapper--aAJhHXD4")
            or css_text("[class*='price'] strong")
            or css_text("[class*='price']")
        )
        price = _parse_price(price_text)
        if link and link.startswith("//"):
            link = "https:" + link
        if image and image.startswith("//"):
            image = "https:" + image

        return {
            "title": title,
            "price": price,
            "image": image,
            "link": link,
        }


def _looks_like_lamp_title(title: str) -> bool:
    lowered = title.lower()
    keywords = [
        "灯",
        "吊灯",
        "壁灯",
        "台灯",
        "落地灯",
        "吸顶灯",
        "灯具",
        "chandelier",
        "lamp",
        "light",
        "ceiling",
        "pendant",
    ]
    return any(key in title or key in lowered for key in keywords)


def _parse_price(raw: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)", str(raw or ""))
    if not match:
        return 0.0
    return float(match.group(1))


def _budget_rank(price: float, budget: str) -> float:
    normalized = str(budget or "未知").strip()
    if normalized == "低":
        return 2.0 if price <= 100 else (1.0 if price <= 180 else -1.0)
    if normalized == "中":
        return 2.0 if 80 <= price <= 300 else (1.0 if price <= 420 else -0.6)
    if normalized == "高":
        return 2.0 if price >= 250 else 0.8
    return 0.6


def _keyword_rank(title: str, keyword: str) -> float:
    score = 0.0
    title = str(title or "")
    for token in re.split(r"\s+", str(keyword or "").strip()):
        if token and token in title:
            score += 1.0
    return score


def select_recommendations(items: list[dict[str, Any]], intent: RecommendIntent, *, limit: int = 3) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        title = str(item.get("title", ""))
        price = float(item.get("price", 0.0) or 0.0)
        score = _keyword_rank(title, intent.keyword) + _budget_rank(price, intent.budget)
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    deduped: list[dict[str, Any]] = []
    seen_links: set[str] = set()
    for _, item in ranked:
        link = str(item.get("link", "")).strip()
        if link and link in seen_links:
            continue
        if link:
            seen_links.add(link)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


class LampRecommendService:
    def __init__(
        self,
        *,
        intent_parser: SiliconFlowIntentParser | None = None,
        taobao_client: TaobaoMarketSpiderClient | None = None,
    ) -> None:
        self.intent_parser = intent_parser or SiliconFlowIntentParser()
        self.taobao_client = taobao_client or TaobaoMarketSpiderClient()

    def recommend(self, user_input: str, *, limit: int = 3) -> dict[str, Any]:
        intent = self.intent_parser.parse(user_input)
        items = self.taobao_client.search_items(intent.keyword, max_items=max(limit * 2, 8))
        recommendations = select_recommendations(items, intent, limit=limit)
        if len(recommendations) < 3:
            raise RuntimeError("未找到足够的灯具商品")
        return {
            "intent": {
                "room": intent.room,
                "brightness": intent.brightness,
                "budget": intent.budget,
                "style": intent.style,
            },
            "keyword": intent.keyword,
            "recommendations": recommendations,
        }
