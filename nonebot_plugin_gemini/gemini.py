import json
import fleep
import base64
import aiohttp
from io import BytesIO
from typing import List, Union
from nonebot.log import logger

from .search_engines import SearchResults
from .model import Response as GeminiResponse


class Gemini:
    def __init__(
        self,
        google_api_key: str,
        search_engine: object = None,
        proxy: str = None,
        *,
        search_prompt: str = None
    ):
        self._proxy = proxy
        self._google_api_key = google_api_key
        self._search_engine = search_engine
        self._search_prompt = search_prompt

    async def generate(
        self,
        contents: Union[List[Union[str, bytes, BytesIO]], str] = "",
        enable_search: bool = False,
        *,
        _contents: list = None,
    ) -> GeminiResponse:
        if enable_search:
            keywords = await self._get_search_keywords(
                contents if _contents is None else _contents[-1]["parts"][0]["text"]
            )

            logger.debug(f"Extracted keywords: {keywords}")

            if keywords != []:
                results: SearchResults = await self._search_engine.get_results(keywords)

                logger.debug(f"Search results: {results}")

                if _contents is None:
                    if isinstance(contents, str):
                        contents = (
                            "\n\n".join(f"{r['title']}\n{r['text']}" for r in results)
                            + "\n\n"
                            + contents
                        )
                    elif isinstance(contents, list):
                        contents = [
                            f"{r['title']}\n{r['text']}" for r in results
                        ] + contents
                else:
                    _contents[-1]["parts"][0]["text"] = (
                        "\n\n".join(f"{r['title']}\n{r['text']}" for r in results)
                        + "\n\n"
                        + _contents[-1]["parts"][0]["text"]
                    )

        model = "gemini-pro"

        if isinstance(contents, str):
            parts = [{"text": contents}]
        elif isinstance(contents, list):
            parts = []
            for content in contents:
                if isinstance(content, str):
                    parts.append({"text": content})
                elif isinstance(content, (bytes, BytesIO)):
                    model = "gemini-pro-vision"
                    info = fleep.get(content[:128])

                    try:
                        mine_type = info.mime[0]
                    except KeyError:
                        raise ValueError("Unable to detect file mime type")

                    parts.append(
                        {
                            "inline_data": {
                                "mime_type": mine_type,
                                "data": self._to_b64(content),
                            }
                        }
                    )
                else:
                    raise ValueError("Unsupported content type")
        else:
            raise ValueError("Unsupported contents type")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._google_api_key}",
                json={
                    "contents": (
                        [
                            {
                                "parts": parts,
                            }
                        ]
                        if _contents is None
                        else _contents
                    )  # 给 GeminiChatSession 用的
                },
                proxy=self._proxy,
            ) as resp:
                if resp.status != 200:
                    raise Exception(
                        f'Status code: {resp.status}, message: {(await resp.json())["error"]["message"]}'
                    )

                data: GeminiResponse = await resp.json()
                return data

    async def _get_search_keywords(
        self, contents: Union[List[Union[str, bytes, BytesIO]], str]
    ) -> List[str]:
        content = (
            contents
            if isinstance(contents, str)
            else "".join([c for c in contents if isinstance(c, str)])
        )

        prompt = f'{self._search_prompt}\nText: {content}'
        result = await self.generate(prompt, enable_search=False)

        try:
            keywords: List[str] = json.loads(
                result["candidates"][0]["content"]["parts"][0]["text"]
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"{type(e).__name__}: Failed to extract keywords, using empty list instead."
            )
            logger.debug(f"Failed to extract keywords: {result}")
            keywords = []

        return keywords

    def _to_b64(self, content: Union[bytes, BytesIO]) -> str:
        if isinstance(content, bytes):
            return base64.b64encode(content).decode()
        elif isinstance(content, BytesIO):
            return base64.b64encode(content.getvalue()).decode()
        else:
            raise ValueError("Unsupported content type")


class GeminiChatSession(Gemini):
    def __init__(
        self,
        google_api_key: str,
        enable_search: bool = False,
        search_engine: object = None,
        proxy: str = None,
        *,
        search_prompt: str = None
    ):
        self.history = []
        self._enable_search = enable_search

        super().__init__(google_api_key, search_engine, proxy, search_prompt=search_prompt)

    async def send_message(self, message: str) -> GeminiResponse:
        self.history.append({"role": "user", "parts": [{"text": message}]})
        resp = await self.generate(
            _contents=self.history, enable_search=self._enable_search
        )
        self.history.append(resp["candidates"][0]["content"])
        return resp
