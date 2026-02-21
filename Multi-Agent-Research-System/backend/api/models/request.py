from typing import List, Optional
from pydantic import BaseModel, field_validator


class ResearchRequest(BaseModel):
    topic: str
    urls: List[str]
    model: Optional[str] = None

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("topic must not be empty")
        return v

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("at least one URL is required")
        if len(v) > 10:
            raise ValueError("maximum 10 URLs allowed")
        for url in v:
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(
                    f"URL must start with http:// or https://: {url}"
                )
        return v
