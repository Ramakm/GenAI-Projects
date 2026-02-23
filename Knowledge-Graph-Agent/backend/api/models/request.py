from pydantic import BaseModel, field_validator


class BuildGraphRequest(BaseModel):
    raw_content: str
    document_title: str
    domain: str = ""
    source_type: str = "text"        # "text" | "url"
    source_identifier: str = "inline"

    @field_validator("raw_content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError("raw_content must be at least 20 characters")
        return v.strip()

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in {"text", "url"}:
            raise ValueError("source_type must be 'text' or 'url'")
        return v


class QueryGraphRequest(BaseModel):
    graph_id: str
    query_text: str
    max_results: int = 15

    @field_validator("query_text")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("query_text must be at least 3 characters")
        return v.strip()
