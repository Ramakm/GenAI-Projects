"""Dataset loading and inspection utilities."""

import logging

import pandas as pd

from schemas import DatasetInfo

logger = logging.getLogger(__name__)


def load_dataset(filepath: str) -> pd.DataFrame:
    """Load a CSV dataset into a pandas DataFrame.

    Args:
        filepath: Path to the CSV file.

    Returns:
        Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed.
    """
    logger.info("Loading dataset: %s", filepath)
    df = pd.read_csv(filepath)
    logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    return df


def get_dataset_info(df: pd.DataFrame, filename: str = "dataset") -> DatasetInfo:
    """Extract metadata from a DataFrame for context injection.

    Args:
        df: The loaded DataFrame.
        filename: Original filename for reference.

    Returns:
        DatasetInfo with schema and sample values.
    """
    sample_values = {}
    for col in df.columns:
        values = df[col].dropna().head(3).astype(str).tolist()
        sample_values[col] = values

    return DatasetInfo(
        filename=filename,
        num_rows=len(df),
        num_columns=len(df.columns),
        columns=list(df.columns),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
        sample_values=sample_values,
    )


def build_context_string(info: DatasetInfo) -> str:
    """Build a context string describing the dataset for the LLM.

    Args:
        info: DatasetInfo metadata.

    Returns:
        Formatted string with dataset details.
    """
    lines = [
        f"Dataset: {info.filename}",
        f"Shape: {info.num_rows} rows x {info.num_columns} columns",
        "",
        "Columns and types:",
    ]
    for col in info.columns:
        dtype = info.dtypes[col]
        samples = ", ".join(info.sample_values.get(col, []))
        lines.append(f"  - {col} ({dtype}): e.g. {samples}")

    return "\n".join(lines)
