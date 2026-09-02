import os

# The production application intentionally requires RAEBURN_API_KEY. Tests provide
# explicit non-production values before importing the app so collection never
# depends on developer services, production credentials, or a local PostgreSQL
# instance.
os.environ.setdefault("RAEBURN_ENV", "test")
os.environ.setdefault("RAEBURN_API_KEY", "test-only-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
