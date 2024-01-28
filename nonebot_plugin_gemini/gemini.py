import fleep
import base64
import aiohttp
from io import BytesIO
from typing import List, Union

from .model import Response as GeminiResponse


class Gemini:
    def __init__(self, google_api_key: str, proxy: str = None):
        self._proxy = proxy
        self._google_api_key = google_api_key

    async def generate(
        self,
        contents: Union[List[Union[str, bytes, BytesIO]], str] = "",
        *,
        _contents: list = None,
    ) -> GeminiResponse:
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
                    parts.append(
                        {
                            "inline_data": {
                                "mime_type": info.mime[0],
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
                    "contents": [
                        {
                            "parts": parts,
                        }
                    ]
                    if _contents is None
                    else _contents  # 给 GeminiChatSession 用的
                },
                proxy=self._proxy,
            ) as resp:
                if resp.status != 200:
                    raise Exception(f'Status code: {resp.status}, message: {(await resp.json())["error"]["message"]}')

                data: GeminiResponse = await resp.json()
                return data

    def _to_b64(self, content: Union[bytes, BytesIO]) -> str:
        if isinstance(content, bytes):
            return base64.b64encode(content).decode()
        elif isinstance(content, BytesIO):
            return base64.b64encode(content.getvalue()).decode()
        else:
            raise ValueError("Unsupported content type")


class GeminiChatSession(Gemini):
    def __init__(self, google_api_key: str, proxy: str = None):
        self.history = []

        super().__init__(google_api_key, proxy)

    async def send_message(self, message: str) -> GeminiResponse:
        self.history.append({"role": "user", "parts": [{"text": message}]})
        resp = await self.generate(_contents=self.history)
        self.history.append(resp["candidates"][0]["content"])
        return resp
