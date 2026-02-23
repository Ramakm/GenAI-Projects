from pydantic import BaseModel, field_validator


class SourceInput(BaseModel):
    type: str       # "rss" | "url" | "text"
    value: str
    label: str = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"rss", "url", "text"}:
            raise ValueError("source type must be 'rss', 'url', or 'text'")
        return v


class AnalyzeRequest(BaseModel):
    topic: str
    query: str = ""
    sources: list[SourceInput]
    time_window: str = "7d"
    topic_id: str | None = None

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("topic must be at least 3 characters")
        return v.strip()

    @field_validator("time_window")
    @classmethod
    def validate_time_window(cls, v: str) -> str:
        if v not in {"24h", "7d", "30d", "all"}:
            raise ValueError("time_window must be '24h', '7d', '30d', or 'all'")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list) -> list:
        if not v:
            raise ValueError("at least one source is required")
        return v


class TopicStoreRequest(BaseModel):
    topic: str
    query: str = ""
    sources: list[SourceInput]
    time_window: str = "7d"
