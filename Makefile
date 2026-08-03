.PHONY: install lint format typecheck test build docker-build

install:
	cd apps/api && python -m pip install --require-hashes -r requirements-dev.lock && python -m pip install --no-deps -e .
	cd apps/web && npm ci

lint:
	cd apps/api && ruff check .
	cd apps/api && ruff format --check .
	cd apps/web && npm run lint

format:
	cd apps/api && ruff format .

typecheck:
	cd apps/api && mypy meeting_intelligence
	cd apps/web && npm run typecheck

test:
	cd apps/api && pytest
	cd apps/web && npm test

build:
	cd apps/web && npm run build

docker-build:
	docker compose build
