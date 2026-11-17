# Pitchcraft pipeline API (Railway).
# Python pipeline + Chromium (scraping) + Pango (WeasyPrint PDFs) + Node/Vercel CLI (prototype deploys).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 libjpeg62-turbo fonts-dejavu-core \
        nodejs npm \
    && npm install -g vercel@latest \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project
RUN playwright install --with-deps chromium

COPY . .
RUN uv sync --no-dev

# Railway volume should be mounted at /app/data so leads + outputs survive redeploys.
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
