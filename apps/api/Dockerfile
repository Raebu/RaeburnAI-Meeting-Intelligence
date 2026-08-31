FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Apply currently available Debian security fixes. Trivy is configured to ignore
# vulnerabilities that do not yet have an upstream fix, so remaining HIGH/CRITICAL
# findings after this step are actionable rather than stale base-layer packages.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/meeting_intelligence ./meeting_intelligence

RUN pip install --no-cache-dir -e .

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz', timeout=3).read()"]

CMD ["uvicorn", "meeting_intelligence.main:app", "--host", "0.0.0.0", "--port", "8080"]
