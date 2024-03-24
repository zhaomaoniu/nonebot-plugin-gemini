from typing import TypedDict, List


class SearchResult(TypedDict):
    title: str
    text: str
    url: str


SearchResults = List[SearchResult]
