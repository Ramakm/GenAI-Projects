"""Node functions for the customer support agent graph."""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import CATEGORIES, ESCALATION_THRESHOLD, MODEL_NAME
from state import AgentState

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model=MODEL_NAME, temperature=0)


def categorize_query(state: AgentState) -> AgentState:
    """Categorize the customer query into a predefined category."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a query classifier for customer support. "
                "Classify the following customer query into exactly one of these categories: "
                "{categories}. "
                "Respond with only the category name, nothing else.",
            ),
            ("human", "{query}"),
        ]
    )

    chain = prompt | llm
    result = chain.invoke(
        {"categories": ", ".join(CATEGORIES), "query": state["customer_query"]}
    )
    category = result.content.strip().lower().replace(" ", "_")

    if category not in CATEGORIES:
        category = "general"

    logger.info("Query categorized as: %s", category)
    return {**state, "category": category}


def analyze_sentiment(state: AgentState) -> AgentState:
    """Analyze the sentiment of the customer query."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a sentiment analyzer. Analyze the sentiment of the customer message. "
                "Respond in JSON format with two fields:\n"
                '- "sentiment": one of "positive", "neutral", "negative", "angry"\n'
                '- "score": a float from -1.0 (very negative) to 1.0 (very positive)\n'
                "Respond with only the JSON, nothing else.",
            ),
            ("human", "{query}"),
        ]
    )

    chain = prompt | llm
    result = chain.invoke({"query": state["customer_query"]})

    try:
        parsed = json.loads(result.content.strip())
        sentiment = parsed.get("sentiment", "neutral")
        score = float(parsed.get("score", 0.0))
    except (json.JSONDecodeError, ValueError):
        sentiment = "neutral"
        score = 0.0

    logger.info("Sentiment: %s (score: %.2f)", sentiment, score)
    return {**state, "sentiment": sentiment, "sentiment_score": score}


def check_escalation(state: AgentState) -> AgentState:
    """Determine if the query needs to be escalated to a human agent."""
    score = state.get("sentiment_score", 0.0)
    sentiment = state.get("sentiment", "neutral")
    category = state.get("category", "general")

    reasons = []

    if score <= ESCALATION_THRESHOLD:
        reasons.append(f"Very negative sentiment (score: {score:.2f})")

    if sentiment == "angry":
        reasons.append("Customer is angry")

    if category == "complaint" and score < 0:
        reasons.append("Negative complaint requires human attention")

    is_escalated = len(reasons) > 0
    escalation_reason = "; ".join(reasons) if reasons else None

    if is_escalated:
        logger.info("Escalation triggered: %s", escalation_reason)

    return {
        **state,
        "is_escalated": is_escalated,
        "escalation_reason": escalation_reason,
    }


def generate_response(state: AgentState) -> AgentState:
    """Generate an appropriate response for the customer query."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful customer support agent. "
                "The customer's query has been categorized as: {category}. "
                "The customer's sentiment is: {sentiment}. "
                "Provide a helpful, professional, and empathetic response. "
                "Be concise but thorough. Address their concern directly.",
            ),
            ("human", "{query}"),
        ]
    )

    chain = prompt | llm
    result = chain.invoke(
        {
            "category": state["category"],
            "sentiment": state["sentiment"],
            "query": state["customer_query"],
        }
    )

    logger.info("Response generated for category: %s", state["category"])
    return {**state, "response": result.content.strip()}


def escalate_to_human(state: AgentState) -> AgentState:
    """Generate an escalation response and flag for human handoff."""
    response = (
        "I understand your concern, and I want to make sure you get the best help possible. "
        "I'm connecting you with a senior support specialist who can assist you further. "
        "Please hold on while I transfer you. "
        f"Your query has been categorized as: {state['category']}."
    )

    logger.info("Query escalated to human agent")
    return {**state, "response": response}
