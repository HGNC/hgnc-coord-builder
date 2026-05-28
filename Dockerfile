FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev default-libmysqlclient-dev pkg-config build-essential git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

ENV UV_PYTHON_PREFERENCE=only-system
ENV UV_PYTHON=python3.13
ENV PYTHONPATH=/app/src:/app

WORKDIR /app

COPY hgnc-coord-builder/pyproject.toml hgnc-coord-builder/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY hgnc-coord-builder/ .
COPY shared/ shared/

RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "--no-sync", "python", "-m", "hgnc_coord_builder"]
