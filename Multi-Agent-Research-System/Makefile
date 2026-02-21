.PHONY: build up down logs pull-model clean test-health test-research

# Build all Docker images
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Tail logs for all services (or pass service=backend etc.)
logs:
	docker compose logs -f $(service)

# Pull the default Ollama model into the running container
pull-model:
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-llama3.2}

# Remove containers, images, and volumes
clean:
	docker compose down -v --rmi local

# Health check
test-health:
	curl -s http://localhost:8000/health | python3 -m json.tool

# Sample research request (2 real URLs)
test-research:
	curl -s -X POST http://localhost:8000/api/research \
	  -H "Content-Type: application/json" \
	  -d '{ \
	    "topic": "Benefits of open source large language models", \
	    "urls": [ \
	      "https://en.wikipedia.org/wiki/Large_language_model", \
	      "https://huggingface.co/blog/open-llm-leaderboard-v2" \
	    ] \
	  }' | python3 -m json.tool
