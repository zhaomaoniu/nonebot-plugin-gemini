from typing import TypedDict, List


class SearchResult(TypedDict):
    title: str
    text: str


SearchResults = List[SearchResult]
