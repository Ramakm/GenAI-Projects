.PHONY: install-backend install-frontend run-backend run-frontend run-all docker-up docker-down pull-model

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && pip install -r requirements.txt

run-backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && streamlit run app.py

run-all:
	make run-backend &
	make run-frontend

pull-model:
	ollama pull llama3.2

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

health:
	curl -s http://localhost:8000/health | python3 -m json.tool
