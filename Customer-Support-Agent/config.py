"""Configuration and environment setup."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4o-mini"

# Sentiment thresholds
ESCALATION_THRESHOLD = -0.6  # Sentiment score below this triggers escalation

# Query categories
CATEGORIES = [
    "billing",
    "technical_support",
    "account_management",
    "product_inquiry",
    "complaint",
    "general",
]
