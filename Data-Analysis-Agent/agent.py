"""PydanticAI agent for natural language data analysis."""

import logging

import pandas as pd
from pydantic_ai import Agent

from config import MODEL_NAME
from data_loader import build_context_string, get_dataset_info
from executor import execute_pandas_code
from schemas import AnalysisResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a data analysis assistant. You receive a dataset description and a natural \
language question about the data. Your job is to generate pandas code that answers \
the question.

Rules:
- The DataFrame is available as `df`. Do NOT load any files.
- Write a single pandas expression or a short block of code.
- For multi-line code, assign the final answer to a variable called `result`.
- Use only pandas and built-in Python. No imports needed.
- Return ONLY the code, no explanations, no markdown fences, no comments.

{dataset_context}
"""


class DataAnalysisAgent:
    """An agent that translates natural language queries into pandas operations."""

    def __init__(self, df: pd.DataFrame, filename: str = "dataset") -> None:
        self.df = df
        self.info = get_dataset_info(df, filename)
        self.context = build_context_string(self.info)

        self.agent = Agent(
            MODEL_NAME,
            system_prompt=SYSTEM_PROMPT.format(dataset_context=self.context),
        )
        logger.info("DataAnalysisAgent initialized for %s", filename)

    def analyze(self, query: str) -> AnalysisResult:
        """Run a natural language query against the dataset.

        Args:
            query: Natural language question about the data.

        Returns:
            AnalysisResult with generated code, result, and any errors.
        """
        logger.info("Processing query: %s", query)

        # Generate pandas code
        result = self.agent.run_sync(query)
        pandas_code = result.data.strip()

        # Clean up code fences if the model included them
        if pandas_code.startswith("```"):
            lines = pandas_code.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            pandas_code = "\n".join(lines).strip()

        logger.info("Generated code:\n%s", pandas_code)

        # Execute the code
        result_text, result_table, error = execute_pandas_code(pandas_code, self.df)

        if error:
            return AnalysisResult(
                query=query,
                pandas_code=pandas_code,
                result_text="Failed to execute the generated query.",
                error=error,
            )

        return AnalysisResult(
            query=query,
            pandas_code=pandas_code,
            result_text=result_text,
            result_data=result_table,
        )
