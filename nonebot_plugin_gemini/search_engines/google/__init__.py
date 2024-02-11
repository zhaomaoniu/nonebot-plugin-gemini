import aiohttp
from typing import List
from nonebot.log import logger

from .models import SearchResponse
from ..models import SearchResult, SearchResults


class GoogleSearch:
    def __init__(
        self, key: str, cx: str = "02f1a2bedcfb14d26", num: int = 3, proxy: str = None
    ) -> None:
        self._params = {"key": key, "cx": cx, "num": num}
        self._proxy = proxy

    async def get_results(self, keywords: List[str]) -> SearchResults:
        params = self._params
        params["q"] = " ".join(keywords)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
                proxy=self._proxy,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Google Custom Search 请求失败: {resp.status}")
                    return []

                search_resp: SearchResponse = await resp.json()

                return [
                    SearchResult(
                        title=item["title"],
                        text=item["snippet"],
                    ) for item in search_resp["items"]
                ]
