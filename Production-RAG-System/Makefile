.PHONY: build up down logs pull-model clean test-health test-upload test-query

# Build all Docker images
build:
	docker compose build

# Start all services in detached mode
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Tail logs from all services (Ctrl+C to exit)
logs:
	docker compose logs -f

# Pull the default LLM model into Ollama (runs inside the ollama container)
pull-model:
	docker compose exec ollama ollama pull $$(grep OLLAMA_MODEL .env | cut -d= -f2 || echo llama3.2)

# Remove containers, volumes, and images built by this project
clean:
	docker compose down -v --rmi local

# Health check
test-health:
	@curl -s http://localhost:8000/health | python3 -m json.tool

# Upload a test document
test-upload:
	@echo "Paris is the capital of France. Berlin is the capital of Germany." > /tmp/rag_test.txt
	@curl -s -X POST http://localhost:8000/api/documents/upload \
		-F "file=@/tmp/rag_test.txt" | python3 -m json.tool

# Run a test query
test-query:
	@curl -s -X POST http://localhost:8000/api/query \
		-H "Content-Type: application/json" \
		-d '{"question": "What is the capital of France?"}' | python3 -m json.tool
