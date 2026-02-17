"""Main entry point for the Customer Support Agent."""

import logging

from graph import agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_agent(query: str) -> dict:
    """Run the customer support agent on a single query.

    Args:
        query: The customer's message.

    Returns:
        Final state dict with category, sentiment, response, and escalation info.
    """
    initial_state = {
        "customer_query": query,
        "category": None,
        "sentiment": None,
        "sentiment_score": None,
        "is_escalated": False,
        "response": None,
        "escalation_reason": None,
    }

    result = agent.invoke(initial_state)
    return result


def print_result(result: dict) -> None:
    """Print the agent result in a readable format."""
    print("\n" + "=" * 60)
    print("CUSTOMER SUPPORT AGENT RESULT")
    print("=" * 60)
    print(f"Query:       {result['customer_query']}")
    print(f"Category:    {result['category']}")
    print(f"Sentiment:   {result['sentiment']} (score: {result['sentiment_score']:.2f})")
    print(f"Escalated:   {result['is_escalated']}")
    if result["escalation_reason"]:
        print(f"Reason:      {result['escalation_reason']}")
    print("-" * 60)
    print(f"Response:\n{result['response']}")
    print("=" * 60 + "\n")


def interactive_mode() -> None:
    """Run the agent in interactive mode."""
    print("Customer Support Agent (type 'quit' to exit)")
    print("-" * 45)

    while True:
        query = input("\nYou: ").strip()
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = run_agent(query)
        print_result(result)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = run_agent(query)
        print_result(result)
    else:
        interactive_mode()
