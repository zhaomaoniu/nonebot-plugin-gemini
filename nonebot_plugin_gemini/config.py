from typing import Optional
from pydantic import BaseModel


class Config(BaseModel):
    google_api_key: Optional[str] = None
