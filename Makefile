.PHONY: install lint format format-check typecheck test build audit security migration-up migration-down migration-check compose-check docker-build verify

PYTHON ?= python

install:
	cd apps/api && $(PYTHON) -m pip install -e '.[dev]'
	cd apps/web && npm install --no-audit --no-fund

lint:
	cd apps/api && ruff check .
	cd apps/web && npm run lint

format:
	cd apps/api && ruff format .

format-check:
	cd apps/api && ruff format --check .

typecheck:
	cd apps/api && mypy meeting_intelligence
	cd apps/web && npm run typecheck

test:
	cd apps/api && pytest
	cd apps/web && npm test

build:
	cd apps/api && $(PYTHON) -m build
	cd apps/web && npm run build

audit:
	cd apps/api && pip-audit --skip-editable
	cd apps/web && npm audit --audit-level=high

security:
	$(PYTHON) scripts/check_secrets.py

migration-up:
	cd apps/api && alembic upgrade head

migration-down:
	cd apps/api && alembic downgrade base

migration-check:
	cd apps/api && rm -f .migration-check.db && DATABASE_URL=sqlite+pysqlite:///./.migration-check.db AUTO_CREATE_SCHEMA=false alembic upgrade head
	cd apps/api && DATABASE_URL=sqlite+pysqlite:///./.migration-check.db AUTO_CREATE_SCHEMA=false alembic downgrade base
	cd apps/api && DATABASE_URL=sqlite+pysqlite:///./.migration-check.db AUTO_CREATE_SCHEMA=false alembic upgrade head
	cd apps/api && rm -f .migration-check.db

compose-check:
	POSTGRES_PASSWORD=compose-validation-only docker compose config --quiet

docker-build:
	docker compose build

verify: lint format-check typecheck test build audit security migration-check compose-check docker-build
