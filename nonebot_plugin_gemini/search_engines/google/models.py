from typing import TypedDict, List


class Url(TypedDict):
    type: str
    template: str


class Request(TypedDict):
    title: str
    totalResults: str
    searchTerms: str
    count: int
    startIndex: int
    inputEncoding: str
    outputEncoding: str
    safe: str
    cx: str


class Queries(TypedDict):
    request: List[Request]
    nextPage: List[Request]


class PagemapOffer(TypedDict):
    pricecurrency: str
    price: str


class PagemapProduct(TypedDict):
    image: str
    name: str


class PagemapAggregateRating(TypedDict):
    reviewcount: str
    ratingvalue: str
    worstrating: str
    description: str
    bestrating: str


class PagemapMetatags(TypedDict):
    og_image: str
    theme_color: str
    twitter_card: str
    twitter_title: str
    og_type: str
    og_title: str
    og_description: str
    twitter_image: str
    fb_app_id: str
    twitter_site: str
    viewport: str
    twitter_description: str
    og_site: str
    og_url: str


class PagemapHproduct(TypedDict):
    fn: str
    photo: str
    currency: str
    currency_iso4217: str


class Pagemap(TypedDict):
    offer: List[PagemapOffer]
    cse_thumbnail: List[dict]
    product: List[PagemapProduct]
    aggregaterating: List[PagemapAggregateRating]
    metatags: List[PagemapMetatags]
    cse_image: List[dict]
    hproduct: List[PagemapHproduct]


class Item(TypedDict):
    kind: str
    title: str
    htmlTitle: str
    link: str
    displayLink: str
    snippet: str
    htmlSnippet: str
    cacheId: str
    formattedUrl: str
    htmlFormattedUrl: str
    pagemap: Pagemap


class SearchResponse(TypedDict):
    kind: str
    url: Url
    queries: Queries
    context: dict
    searchInformation: dict
    items: List[Item]
