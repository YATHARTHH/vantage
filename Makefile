.PHONY: install dev dev-app test test-unit test-integration lint format seed migrate clean

install:
	uv sync --all-groups

dev:
	docker compose up --build

dev-app:
	uv run fastapi dev vantage/api/app.py

test:
	uv run pytest tests/ -v --cov=vantage --cov-report=term-missing

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

lint:
	uv run ruff check vantage/ tests/
	uv run mypy vantage/

format:
	uv run ruff format vantage/ tests/

seed:
	uv run python scripts/seed_data.py

migrate:
	uv run alembic upgrade head

clean:
	if exist data rmdir /s /q data
	if exist .mypy_cache rmdir /s /q .mypy_cache
	if exist .ruff_cache rmdir /s /q .ruff_cache
	for /r . %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
