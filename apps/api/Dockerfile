FROM python:3.12-alpine3.24@sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b AS build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apk add --no-cache build-base
COPY apps/api/requirements.lock ./requirements.lock
RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir --require-hashes -r requirements.lock \
    && rm -rf /opt/venv/lib/python3.12/site-packages/pip* \
        /opt/venv/lib/python3.12/site-packages/setuptools* \
        /opt/venv/lib/python3.12/site-packages/wheel* \
        /opt/venv/bin/pip*

FROM python:3.12-alpine3.24@sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip* \
        /usr/local/lib/python3.12/site-packages/setuptools* \
        /usr/local/lib/python3.12/site-packages/wheel* \
        /usr/local/bin/pip* \
    && addgroup -S app \
    && adduser -S -G app app
COPY --from=build /opt/venv /opt/venv
COPY apps/api/meeting_intelligence ./meeting_intelligence
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).read()"]
CMD ["uvicorn", "meeting_intelligence.main:app", "--host", "0.0.0.0", "--port", "8080"]
