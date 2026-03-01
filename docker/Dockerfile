# Multi-stage build for minimal runtime image
# Based on https://github.com/astral-sh/uv-docker-example/

ARG PYTHON_VER=3.13

# ============ Builder ============
FROM python:${PYTHON_VER}-alpine AS builder

# Copy uv binary from official image (version pinned to match CI)
COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --no-editable

# Copy source and install project as package
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ============ Runtime ============
FROM python:${PYTHON_VER}-alpine

# Non-root user for security
RUN addgroup -S -g 456 nonroot \
    && adduser -S -u 456 -G nonroot -D -s /bin/sh nonroot

# Copy only the venv (contains installed package) and default inventory
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --from=builder --chown=nonroot:nonroot /app/docker/inventory.yaml /app/docker/inventory.yaml

ENV PATH="/app/.venv/bin:$PATH"

USER nonroot

CMD ["simnos", "-i", "/app/docker/inventory.yaml"]
