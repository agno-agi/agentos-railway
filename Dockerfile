# ===========================================================================
# Shared runtime
# ===========================================================================
FROM agnohq/python:3.14 AS base

USER root
WORKDIR /app
COPY requirements.txt ./
RUN uv pip sync requirements.txt --system

# ===========================================================================
# Sandbox (Docker and AgentCore)
# ===========================================================================
FROM base AS sandbox

ENV HOME=/runtime
WORKDIR /workspace

# sandbox supervisor runs as root; agent commands run as UID 1000.
RUN groupadd --gid 1000 sandbox \
    && useradd --uid 1000 --gid 1000 --home-dir /runtime --no-create-home sandbox

EXPOSE 8080
ENTRYPOINT ["python", "-I", "-m", "agno.sandbox.agentcore.server", "serve"]
CMD []

# ===========================================================================
# AgentOS (default target)
# ===========================================================================
FROM base AS agentos

ENV PYTHONPATH=/app
COPY . .

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# ---------------------------------------------------------------------------
# Default command (overridden by compose for dev)
# ---------------------------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
