.PHONY: dev migrate upgrade lint test generate-admin-key

dev:
	uvicorn app.main:app --reload --port 8001

migrate:
	alembic revision --autogenerate -m "$(msg)"

upgrade:
	alembic upgrade head

lint:
	ruff check app/

test:
	pytest tests/ -v

generate-admin-key:
	python -c "import secrets; print(secrets.token_urlsafe(32))"
