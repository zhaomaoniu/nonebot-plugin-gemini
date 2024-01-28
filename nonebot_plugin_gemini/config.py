from typing import Optional
from pydantic import BaseModel


class Config(BaseModel):
    google_api_key: Optional[str] = None
    proxy: Optional[str] = None
    image_render_length: Optional[int] = 500
