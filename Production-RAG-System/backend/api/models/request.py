from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question to answer")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")
    filter_source: Optional[str] = Field(None, description="Filter results to a specific source filename")


class StreamQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The question to answer")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve")
