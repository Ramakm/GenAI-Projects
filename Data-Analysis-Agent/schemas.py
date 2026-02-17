"""Pydantic models for structured agent input and output."""

from typing import Optional

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    """Metadata about the loaded dataset."""

    filename: str
    num_rows: int
    num_columns: int
    columns: list[str]
    dtypes: dict[str, str]
    sample_values: dict[str, list[str]]


class AnalysisResult(BaseModel):
    """Structured result from a data analysis query."""

    query: str = Field(description="The original natural language query")
    pandas_code: str = Field(description="The generated pandas code")
    result_text: str = Field(description="Human-readable answer")
    result_data: Optional[str] = Field(
        default=None, description="Tabular result if applicable"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
