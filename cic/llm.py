from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_CODING_BASE_URL = "https://open.bigmodel.cn/api/coding/paas/v4"


@dataclass(slots=True)
class LLMResult:
    data: dict[str, Any]
    status: str
    error: str = ""


class LLMClient:
    """Small OpenAI-compatible chat-completions client.

    The Coding Plan endpoint documented by Zhipu uses a dedicated base URL. The
    code keeps the key in environment variables only and never logs request
    headers.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("ZHIPU_BASE_URL") or os.getenv("LLM_BASE_URL") or DEFAULT_CODING_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else (os.getenv("ZHIPU_API_KEY") or os.getenv("LLM_API_KEY") or "")
        self.model = model or os.getenv("ZHIPU_MODEL") or os.getenv("LLM_MODEL") or "glm-5.1"
        self.timeout_seconds = timeout_seconds or float(os.getenv("LLM_TIMEOUT_SECONDS") or 90)

    def chat_json(self, system_prompt: str, user_prompt: str, fallback: dict[str, Any]) -> LLMResult:
        if not self.api_key:
            return LLMResult(fallback, "skipped_no_api_key")

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
            parsed = json.loads(body)
            content = parsed["choices"][0]["message"]["content"]
            return LLMResult(extract_json_object(content, fallback), "ok")
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError) as exc:
            return LLMResult(fallback, "fallback_after_error", sanitize_error(str(exc)))


def extract_json_object(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return fallback
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return fallback
    return parsed if isinstance(parsed, dict) else fallback


def sanitize_error(error: str) -> str:
    # Keep enough detail for debugging while avoiding accidental credential echo.
    return re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", error)[:300]


def heuristic_insights(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for holding in holdings:
        risks = holding.get("risks", []) or []
        missing = ["更高等级来源验证", "财务兑现数据"]
        if holding.get("pe_percentile_5y", 0.5) > 0.75:
            missing.append("估值消化")
        if holding.get("stock_20d_return", 0) > 0.2:
            risks = [*risks, "短期涨幅较大，可能存在交易拥挤"]
        items.append(
            {
                "stock_code": holding["stock_code"],
                "evidence_missing": missing,
                "counter_evidence": risks or ["缺少同业比较和财务兑现证据"],
                "research_question": f"{holding['stock_name']} 的核心假设是否能被下一次公告、财报或行业数据验证？",
            }
        )
    return {"items": items}


def build_research_prompt(holdings: list[dict[str, Any]]) -> tuple[str, str]:
    system = (
        "你是 A 股投研驾驶舱的反方与研究问题生成器。"
        "只输出 JSON，不输出 Markdown。"
        "不要给无条件买卖建议。"
        "每只股票输出 evidence_missing、counter_evidence、research_question。"
    )
    user = {
        "task": "为每个持仓生成缺失证据、反方证据和下一研究问题。",
        "schema": {
            "items": [
                {
                    "stock_code": "000001.SZ",
                    "evidence_missing": ["string"],
                    "counter_evidence": ["string"],
                    "research_question": "string",
                }
            ]
        },
        "holdings": holdings,
    }
    return system, json.dumps(user, ensure_ascii=False)
