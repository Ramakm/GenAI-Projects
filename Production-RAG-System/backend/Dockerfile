FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Pre-download the embedding model into the image so the first upload
# doesn't incur a 30-60s cold-start delay in production.
RUN python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
import os; \
model = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'); \
HuggingFaceEmbeddings(model_name=model, encode_kwargs={'normalize_embeddings': True}); \
print('Embedding model pre-downloaded successfully.')"

# One worker only — FAISS IndexFlatL2 is not safe across multiple processes.
# Use threading.Lock within the single process instead.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
