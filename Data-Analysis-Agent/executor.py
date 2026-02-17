"""Safe execution of generated pandas code."""

import logging
import io
from typing import Optional

import pandas as pd
from tabulate import tabulate

logger = logging.getLogger(__name__)

ALLOWED_MODULES = {"pd": pd}


def execute_pandas_code(
    code: str, df: pd.DataFrame
) -> tuple[str, Optional[str], Optional[str]]:
    """Execute generated pandas code safely against a DataFrame.

    Args:
        code: Python/pandas code string to execute.
        df: The DataFrame to operate on (available as 'df' in the code).

    Returns:
        Tuple of (result_text, result_table_or_none, error_or_none).
    """
    local_vars = {"df": df, "pd": pd}

    try:
        # Capture the last expression result
        exec_code = code.strip()
        result = None

        # Try eval first for single expressions
        try:
            result = eval(exec_code, {"__builtins__": {}}, local_vars)
        except SyntaxError:
            # Fall back to exec for multi-line code
            exec(exec_code, {"__builtins__": {}}, local_vars)
            result = local_vars.get("result", None)

        # Format the result
        result_text, result_table = _format_result(result)
        logger.info("Code executed successfully")
        return result_text, result_table, None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error("Execution failed: %s", error_msg)
        return "", None, error_msg


def _format_result(result: object) -> tuple[str, Optional[str]]:
    """Format an execution result into text and optional table.

    Args:
        result: The result from code execution.

    Returns:
        Tuple of (text_description, table_string_or_none).
    """
    if result is None:
        return "Query executed successfully (no return value).", None

    if isinstance(result, pd.DataFrame):
        if result.empty:
            return "The query returned an empty DataFrame.", None
        table = tabulate(result.head(20), headers="keys", tablefmt="grid", showindex=True)
        text = f"Result: DataFrame with {len(result)} rows and {len(result.columns)} columns."
        if len(result) > 20:
            text += " (showing first 20 rows)"
        return text, table

    if isinstance(result, pd.Series):
        if result.empty:
            return "The query returned an empty Series.", None
        table = tabulate(
            result.head(20).reset_index(),
            headers="keys",
            tablefmt="grid",
            showindex=False,
        )
        text = f"Result: Series with {len(result)} entries."
        return text, table

    return str(result), None
