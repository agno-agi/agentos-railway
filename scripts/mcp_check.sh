#!/usr/bin/env bash

############################################################################
#
#    Agno MCP Smoke Check
#
#    Checks the handshake and required tools. Additional tools are welcome.
#    Model calls happen only when --prompt is supplied.
#
#    Usage:
#      ./scripts/mcp_check.sh
#      ./scripts/mcp_check.sh --prompt "Introduce yourself briefly."
#      MCP_CHECK_HOST=1 ./scripts/mcp_check.sh
#
#    The client runs inside agentos-api by default; host mode uses uv/.env.
#    Set AGENTOS_URL to override the endpoint and export MCP_CHECK_TOKEN
#    for an authenticated endpoint (an existing JWT or PAT).
#
############################################################################

set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
    echo 'Usage: ./scripts/mcp_check.sh [--prompt "message"]'
    echo 'Default: handshake and required tools only (no model call).'
    echo 'Use MCP_CHECK_HOST=1 for a host client, AGENTOS_URL for the server,'
    echo 'and MCP_CHECK_TOKEN for an existing bearer token.'
}

prompt=""
case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    --prompt)
        if [[ $# -ne 2 || -z "${2:-}" ]]; then usage >&2; exit 2; fi
        prompt="$2"
        ;;
    *) if [[ $# -ne 0 ]]; then usage >&2; exit 2; fi ;;
esac

runner=(docker compose exec -T)
for name in MCP_CHECK_TOKEN AGENTOS_URL; do
    if [[ -n "${!name:-}" ]]; then runner+=(-e "$name"); fi
done
runner+=(agentos-api python -u)
if [[ "${MCP_CHECK_HOST:-0}" == 1 ]]; then
    runner=(uv run --no-project --env-file .env --with-requirements requirements.txt python -u)
fi

echo ""
echo -e '\033[38;5;208m▸\033[0m \033[1mMCP Check\033[0m'
if [[ -n "$prompt" ]]; then echo 'Mode: includes a model call (--prompt).'; fi
exec "${runner[@]}" - "$prompt" <<'PY'
import asyncio
import os
import sys

from httpx2 import AsyncClient, HTTPStatusError, RequestError, TimeoutException
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import PaginatedRequestParams

REQUIRED = {
    "agno", "get_agentos_config", "run_agent", "run_team", "run_workflow",
    "continue_run", "cancel_run", "get_sessions", "get_session_runs",
}


def explain(error):
    if isinstance(error, BaseExceptionGroup):
        return "; ".join(dict.fromkeys(explain(item) for item in error.exceptions))
    if isinstance(error, HTTPStatusError):
        status = error.response.status_code
        if status in (401, 403):
            return f"HTTP {status}: check MCP_CHECK_TOKEN and its permissions"
        return f"HTTP {status}: check AGENTOS_URL and the API logs"
    if isinstance(error, (TimeoutError, TimeoutException)):
        return "timed out waiting for MCP; check the API logs"
    if isinstance(error, RequestError):
        return "cannot reach MCP; check AGENTOS_URL and that the API is running"
    return " ".join(str(error).split()) or type(error).__name__


async def check_response(response):
    # Preserve HTTP diagnostics before the MCP transport turns them into a
    # generic protocol error. GET/DELETE may legitimately be unsupported.
    if response.request.method == "POST":
        response.raise_for_status()


async def main():
    prompt = sys.argv[1]
    url = os.getenv("AGENTOS_URL", "http://localhost:8000").rstrip("/") + "/mcp"
    print(f"Endpoint: {url}")
    token = os.getenv("MCP_CHECK_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    timeout = 180 if prompt else 30
    async with asyncio.timeout(timeout), AsyncClient(
        headers=headers, timeout=timeout, event_hooks={"response": [check_response]}
    ) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, *_):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✓ Handshake")
                names, cursor = set(), None
                while True:
                    page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor))
                    names.update(tool.name for tool in page.tools)
                    cursor = page.next_cursor
                    if not cursor:
                        break
                if missing := REQUIRED - names:
                    raise RuntimeError(f"missing required tools: {', '.join(sorted(missing))}")
                print(f"✓ {len(names)} tools; required tools available")
                if prompt:
                    result = await session.call_tool("agno", {"message": prompt})
                    answer = "\n".join(item.text for item in result.content if hasattr(item, "text"))
                    if result.is_error:
                        raise RuntimeError(f"agno tool failed: {answer or 'see API logs'}")
                    print(f"✓ agno responded\n\n{answer}")
    print("\nDone.")


try:
    asyncio.run(main())
except Exception as error:
    print(f"Failed: {explain(error)}", file=sys.stderr)
    sys.exit(1)
PY
