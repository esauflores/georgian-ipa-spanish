FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
ENV UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group audio
COPY data ./data
COPY src ./src
COPY scripts ./scripts
RUN .venv/bin/python -m scripts.generate_audio && uv sync --locked --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
COPY --from=build /app/data /app/data
ENV DICTIONARY_READ_ONLY=1
CMD ["sh", "-c", "exec .venv/bin/uvicorn main:app --app-dir src --host 0.0.0.0 --port \"${PORT:-8000}\""]
