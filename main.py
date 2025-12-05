import re
from typing import List, Dict, Any

import httpx

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig


@register("abbr", "XSana", "调用nbnhhsh，获取缩写", "1.0.0")
class EatWhat(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.api_url = self.config.get("api_url")

    @filter.command("abbr", alias={"缩写", "nbnhhsh", "hhsh"})
    async def abbr(self, event: AstrMessageEvent, text: str):
        result_text = "没有匹配到拼音首字母缩写"

        if not re.fullmatch(r"[a-zA-Z0-9]+", text):
            result_text = "仅支持由英文字母或数字组成的缩写，例如：hhsh"
        else:
            data = await self.guess(text)
            if data:
                item = data[0]
                name = item.get("name", "") or ""
                trans = item.get("trans")

                if trans:
                    meaning = "，".join(trans)
                    result_text = f"{name}：{meaning}"

        yield event.plain_result(result_text)
        event.stop_event()

    async def guess(self, text: str) -> List[Dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return []

        payload = {"text": text}
        _timeout = httpx.Timeout(timeout=5.0, connect=5.0)
        async with httpx.AsyncClient(timeout=_timeout) as client:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            logger.warning(f"[abbr] 非预期响应结构: {data!r}")
            return []

        return data

    async def terminate(self):
        logger.info("[abbr] plugin terminated")
