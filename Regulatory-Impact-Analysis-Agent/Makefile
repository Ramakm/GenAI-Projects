.PHONY: install run-backend run-frontend run docker-up docker-down pull-model

install:
	cd backend && pip install -r requirements.txt
	cd frontend && pip install -r requirements.txt

run-backend:
	cd backend && uvicorn main:app --reload --port 8000

run-frontend:
	cd frontend && streamlit run app.py --server.port 8501

run:
	@echo "Starting backend and frontend..."
	@(cd backend && uvicorn main:app --reload --port 8000 &)
	@(cd frontend && streamlit run app.py --server.port 8501)

docker-up:
	docker compose up --build

docker-down:
	docker compose down

pull-model:
	ollama pull llama3.2
