.PHONY: install lint format typecheck test build docker-build

install:
	cd apps/api && python -m pip install -e .[dev]
	cd apps/web && npm install

lint:
	cd apps/api && ruff check .
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
