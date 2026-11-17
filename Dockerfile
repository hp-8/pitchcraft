# Pitchcraft pipeline API (Render).
# Python pipeline + Chromium (scraping) + Pango (WeasyPrint PDFs) + Node/Vercel CLI (prototype deploys).
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 libjpeg62-turbo fonts-dejavu-core \
        nodejs npm \
    && npm install -g vercel@latest \
    && rm -rf /var/lib/apt/lists/*

# Same uv that wrote uv.lock, so the lockfile format always matches.
RUN pip install --no-cache-dir "uv==0.13.9"

WORKDIR /app
# Deps layer: cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
RUN python -m playwright install --with-deps chromium

COPY . .
RUN uv sync --locked --no-dev

# Persistent disk (paid Render plans) should be mounted at /app/data so leads + outputs survive redeploys.
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
