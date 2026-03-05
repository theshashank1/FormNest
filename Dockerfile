# ========================================
# FormNest — Multi-stage Dockerfile
# ========================================

# --- Base ---
FROM python:3.12-slim AS base
WORKDIR /app
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY server/ server/
COPY alembic/ alembic/
COPY alembic.ini .
COPY run.py run_workers.py ./

# --- API Target ---
FROM base AS api
EXPOSE 8001
CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8001"]

# --- Workers Target ---
FROM base AS workers
CMD ["uv", "run", "python", "run_workers.py"]
