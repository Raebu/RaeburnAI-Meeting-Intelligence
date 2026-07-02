FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/meeting_intelligence ./meeting_intelligence

RUN pip install --no-cache-dir -e .

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "meeting_intelligence.main:app", "--host", "0.0.0.0", "--port", "8080"]
