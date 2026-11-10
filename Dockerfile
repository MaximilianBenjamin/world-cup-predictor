# The hosted site: the built frontend plus the API, serving the predictions in
# data/live/site.json. It fits no models; the daily GitHub Actions run does that
# and commits the file, and a new image is built from it.
#
#   docker build -t zuba . && docker run -p 8001:8001 zuba

# ---- frontend ----
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Python dependencies ----
FROM python:3.12-slim AS python
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
# Dependencies first, so this layer is reused when only the source changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ---- runtime ----
FROM python:3.12-slim
# LightGBM and XGBoost need the OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:${PATH}" ZUBA_DB=/tmp/zuba.db
WORKDIR /app
COPY --from=python /app /app
COPY --from=frontend /frontend/dist ./frontend/dist
# The season record reads this season's results and the backtest files.
COPY data/clubs/ ./data/clubs/
COPY data/live/ ./data/live/
COPY data/backtest_epl_predictions.csv ./data/
COPY docs/backtest_epl.json ./docs/
RUN useradd --create-home zuba
USER zuba
EXPOSE 8001
CMD ["uvicorn", "zuba.api.app:app", "--host", "0.0.0.0", "--port", "8001"]
