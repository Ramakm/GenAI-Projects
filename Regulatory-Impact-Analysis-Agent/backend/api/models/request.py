from pydantic import BaseModel, HttpUrl, field_validator, model_validator


class URLIngestRequest(BaseModel):
    url: HttpUrl
    industry: str = "auto"


class TextIngestRequest(BaseModel):
    content: str
    title: str
    industry: str = "auto"

    @field_validator("content")
    @classmethod
    def content_min_length(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("Content must be at least 50 characters")
        return v


class RSSIngestRequest(BaseModel):
    feed_url: HttpUrl
    max_entries: int = 5
    industry: str = "auto"


class AnalysisRequest(BaseModel):
    # Option A: reference a previously ingested source
    source_id: str | None = None

    # Option B: inline content
    raw_content: str | None = None
    source_type: str | None = None          # "pdf" | "url" | "text" | "rss"
    source_identifier: str | None = None

    industry: str = "auto"

    @model_validator(mode="after")
    def validate_source(self) -> "AnalysisRequest":
        if not self.source_id and not self.raw_content:
            raise ValueError("Provide either source_id or raw_content + source_type")
        return self
