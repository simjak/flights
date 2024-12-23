.PHONY: setup migrate test lint run clean

setup:
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv venv
	uv pip sync
	alembic upgrade head

migrate:
	alembic revision --autogenerate -m "$(message)"
	alembic upgrade head

test:
	uv pip sync --group dev
	pytest tests/ -v --cov=src

lint:
	uv pip sync --group dev
	black .
	isort .
	ruff check .
	mypy src/

run:
	docker-compose up --build

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	rm -rf .venv/