from typing import Optional
from pydantic import BaseModel


class Config(BaseModel):
    # Gemini
    google_api_key: Optional[str] = None
    proxy: Optional[str] = None
    image_render_length: Optional[int] = 500

    # Google Custom Search
    enable_search: Optional[bool] = False
    google_custom_search_key: str
    google_custom_search_cx: Optional[str] = "02f1a2bedcfb14d26"
    google_custom_search_num: Optional[int] = 3
    search_keywords_prompt: Optional[str] = 'Please extract the keywords from the following text and output them in JSON Array format, the keywords will be using for searching. If there is not a clear subject, just give an empty array. For example, an expected output for "原神是什么" is ["原神"], an expected output for "这是什么" is [], an expected output for "为什么要演奏春日影" is ["为什么","演奏","春日影"], an expected output for "今天是几号" is ["今天","几号"].'
