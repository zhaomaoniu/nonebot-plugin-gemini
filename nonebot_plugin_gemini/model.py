from typing import List, TypedDict


class Part(TypedDict):
    text: str


class Content(TypedDict):
    parts: List[Part]
    role: str


class SafetyRating(TypedDict):
    category: str
    probability: str


class Candidate(TypedDict):
    content: Content
    finishReason: str
    index: int
    safetyRatings: List[SafetyRating]


class PromptFeedback(TypedDict):
    safetyRatings: List[SafetyRating]


class Response(TypedDict):
    candidates: List[Candidate]
    promptFeedback: PromptFeedback
