# syntax=docker/dockerfile:1
# Bot backend image. Build from the repository root:
#   docker build -f apps/bot/Dockerfile -t campus-agent-bot .

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

# --- build stage: resolve and install into /app/.venv --------------------------------
FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_DEV=1
WORKDIR /app

# Dependencies first for layer caching: only the workspace metadata.
COPY pyproject.toml uv.lock ./
COPY core/pyproject.toml core/
COPY integrations/pyproject.toml integrations/
COPY modules/members/pyproject.toml modules/members/
COPY modules/certificates/pyproject.toml modules/certificates/
COPY modules/knowledge/pyproject.toml modules/knowledge/
COPY modules/events/pyproject.toml modules/events/
COPY apps/bot/pyproject.toml apps/bot/
COPY apps/mcp/pyproject.toml apps/mcp/
COPY apps/cli/pyproject.toml apps/cli/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-workspace --package campus-agent-bot

# Then the sources, installed as regular (non-editable) packages.
COPY core core
COPY integrations integrations
COPY modules modules
COPY apps/bot apps/bot
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --package campus-agent-bot

# --- runtime stage: no uv, no sources, non-root ---------------------------------------
FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    BOT_BIND_HOST=0.0.0.0 \
    BOT_PORT=3978
WORKDIR /app
USER app
EXPOSE 3978
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3978/healthz', timeout=4)"]
CMD ["campus-agent-bot"]
