"""Configuration and environment setup."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "openai:gpt-4o-mini"
MAX_RETRIES = 3
