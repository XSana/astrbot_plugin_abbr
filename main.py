import re
from typing import List, Dict, Any

import httpx

from astrbot.api import logger, llm_tool
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig


@register("abbr", "XSana", "调用nbnhhsh，获取缩写", "1.2.1")
class Abbr(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.api_url = self.config.get("api_url")
        self.ignore_prefix = self.config.get("ignore_prefix")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_keyword_detect(self, event: AstrMessageEvent):
        """
        监听所有类型的消息事件，当启用 ignore_prefix 配置时，
        检查消息是否以指定的命令关键词开头（如 abbr、缩写等），
        如果匹配成功则触发缩写查询功能。
        """
        if not self.ignore_prefix:
            return

        text = (event.message_str or "").strip()
        if not text:
            return

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        if cmd not in {"abbr", "缩写", "nbnhhsh", "hhsh"}:
            return

        if len(parts) < 2:
            result_text = "请在指令后带上要查询的缩写"
        else:
            result_text = await self._query_abbr(parts[1])

        yield event.plain_result(result_text)
        event.stop_event()

    @filter.command("abbr", alias={"缩写", "nbnhhsh", "hhsh"})
    async def abbr(self, event: AstrMessageEvent):
        """
        调用 nbnhhsh API 发送请求，并将结果格式化后返回给用户。
        支持的命令别名包括：缩写、nbnhhsh、hhsh。
        """
        message_text = (event.message_str or "").strip()

        parts = message_text.split(maxsplit=1)
        if len(parts) < 2:
            result_text = "请在指令后带上要查询的缩写"
        else:
            result_text = await self._query_abbr(parts[1])

        yield event.plain_result(result_text)
        event.stop_event()

    @llm_tool("abbr")
    async def abbr_tool(self, event: AstrMessageEvent, text: str = None):
        """
        Call this tool when the user is asking for the meaning of an abbreviation.
        Use this tool in (at least) the following situations:
        1) The user explicitly asks for the meaning / explanation of a short string that
           looks like an abbreviation, e.g.:
           - "zssm是什么意思"
           - "帮我查一下zssm"
           - "解释一下这个缩写：ysmd"
           - "zssm是什么"
        2) The user sends a short token mainly composed of letters and/or digits (e.g. "nb666",
           "xswl", "zssm") and asks what it means, how to read it, or asks for an explanation.

        Args:
            text (string): Required. The abbreviation to query. This should be the core token
                (letters/digits only) extracted from the user's message, such as "zssm".
        """
        result_text = await self._query_abbr(text)
        if not result_text:
            result_text = "请在指令后带上要查询的缩写"
        yield event.plain_result(result_text)

    async def _query_abbr(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        if not re.fullmatch(r"[a-zA-Z0-9]+", text):
            return "仅支持由英文字母或数字组成的缩写，例如：zssm"

        data = await self.guess(text)
        if data:
            item = data[0]
            name = item.get("name", "") or ""
            trans = item.get("trans")
            if trans:
                meaning = "，".join(trans)
                return f"{name}：{meaning}"

        return "没有匹配到拼音首字母缩写"

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
