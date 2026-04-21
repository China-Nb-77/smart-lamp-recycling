up:
	docker compose up --build

down:
	docker compose down

openapi:
	python backend/scripts/export_openapi.py

frontend-api:
	cd frontend && npm run generate:api

test:
	pytest tests/test_agent_api.py

