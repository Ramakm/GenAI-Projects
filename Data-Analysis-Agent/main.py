"""Main entry point for the Data Analysis Agent."""

import argparse
import logging
import sys

from agent import DataAnalysisAgent
from data_loader import load_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def print_result(result) -> None:
    """Print an analysis result in a readable format."""
    print("\n" + "=" * 60)
    print("DATA ANALYSIS RESULT")
    print("=" * 60)
    print(f"Query:  {result.query}")
    print(f"Code:   {result.pandas_code}")
    print("-" * 60)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(result.result_text)
        if result.result_data:
            print()
            print(result.result_data)

    print("=" * 60 + "\n")


def interactive_mode(agent: DataAnalysisAgent) -> None:
    """Run the agent in interactive mode."""
    print("Data Analysis Agent (type 'quit' to exit)")
    print(f"Dataset: {agent.info.filename} ({agent.info.num_rows} rows, {agent.info.num_columns} columns)")
    print(f"Columns: {', '.join(agent.info.columns)}")
    print("-" * 50)

    while True:
        query = input("\nAsk: ").strip()
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = agent.analyze(query)
        print_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data Analysis Agent -- ask questions about your data in plain English"
    )
    parser.add_argument(
        "--data",
        default="sample_data.csv",
        help="Path to CSV file (default: sample_data.csv)",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Single query to run (omit for interactive mode)",
    )
    args = parser.parse_args()

    df = load_dataset(args.data)
    agent = DataAnalysisAgent(df=df, filename=args.data)

    if args.query:
        result = agent.analyze(args.query)
        print_result(result)
    else:
        interactive_mode(agent)


if __name__ == "__main__":
    main()
