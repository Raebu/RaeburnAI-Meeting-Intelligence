import os

os.environ["RAEBURN_ENV"] = "test"
os.environ["RAEBURN_API_KEY"] = "test-api-key-not-a-production-secret"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AUTO_CREATE_SCHEMA"] = "true"
os.environ["RAEBURN_CORS_ORIGINS"] = "http://testserver"
os.environ["RAEBURN_RATE_LIMIT_PER_MINUTE"] = "1000"
