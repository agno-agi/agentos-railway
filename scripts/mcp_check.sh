#!/bin/bash

############################################################################
#
#    MCP Smoke Check
#
#    Proves the AgentOS MCP endpoint end to end: handshake, tool count,
#    then one run_agent call. The default question tells the agent to skip
#    its tools, so the whole check finishes in seconds. Runs the client
#    inside the container.
#
#    When /mcp is auth-gated (MCP_CONNECT_SECRET set, or prd JWT), the
#    check mints a short-lived probe service account, runs authenticated,
#    and deletes the account afterwards — even on failure.
#
#    Usage:
#      ./scripts/mcp_check.sh                            # quick default probe
#      ./scripts/mcp_check.sh "What does the platform run?"  # your own question
#
############################################################################

set -e

# Colors
ORANGE='\033[38;5;208m'
RED='\033[31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

DEFAULT_QUESTION="Without using any tools, introduce yourself and this platform in two short sentences."
QUESTION="${1:-$DEFAULT_QUESTION}"

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}MCP Check${NC}"
echo ""
echo -e "${DIM}> http://localhost:8000/mcp  (client runs inside agentos-api)${NC}"
echo ""

if docker compose exec -T agentos-api python -u - "$QUESTION" <<'PY'
import asyncio
import sys
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ORANGE = "\033[38;5;208m"
DIM = "\033[2m"
BOLD = "\033[1m"
NC = "\033[0m"


def step(text: str) -> None:
    print(f"{ORANGE}✓{NC} {text}", flush=True)


async def run_check(headers: dict | None, auth_note: str) -> None:
    async with streamablehttp_client("http://localhost:8000/mcp", headers=headers, timeout=180) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            step(f"Handshake — {auth_note}")
            tools = await session.list_tools()
            step(f"MCP OK — {len(tools.tools)} tools")
            start = time.perf_counter()
            result = await session.call_tool(
                "run_agent",
                {"agent_id": "platform-manager", "message": sys.argv[1]},
                read_timeout_seconds=None,
            )
            elapsed = time.perf_counter() - start
            step(f"run_agent — platform-manager answered in {elapsed:.1f}s")
            # run_agent returns a trimmed ToolResult: content[0].text is the plain
            # answer, and structuredContent carries {run_id, session_id, status}.
            print(flush=True)
            print(f"{DIM}Agent response:{NC}", flush=True)
            print(flush=True)
            print(result.content[0].text, flush=True)


def is_unauthorized(exc: BaseException) -> bool:
    """True when the failure chain contains an HTTP 401 (auth-gated /mcp)."""
    if isinstance(exc, BaseExceptionGroup):
        return any(is_unauthorized(e) for e in exc.exceptions)
    return "401" in str(exc) or any(is_unauthorized(e) for e in (exc.__cause__, exc.__context__) if e)


async def run_check_with_probe_pat() -> None:
    """Mint a probe service account, run authenticated, always delete it."""
    import time as _time
    import uuid

    from agno.db.schemas.service_accounts import ServiceAccount
    from agno.os.service_accounts import DEFAULT_SERVICE_ACCOUNT_SCOPES, generate_token
    from db import get_postgres_db

    db = get_postgres_db()
    plaintext, token_hash, token_prefix = generate_token()
    now = int(_time.time())
    account = ServiceAccount(
        id=str(uuid.uuid4()),
        name=f"mcp-check-probe-{now}",
        token_hash=token_hash,
        token_prefix=token_prefix,
        scopes=list(DEFAULT_SERVICE_ACCOUNT_SCOPES),
        created_at=now,
        expires_at=now + 600,
        created_by="mcp_check.sh",
        user_id=None,
    )
    db.create_service_account(account.to_dict())
    try:
        await run_check(
            {"Authorization": f"Bearer {plaintext}"},
            "auth-gated; connected with a short-lived probe token",
        )
    finally:
        db.delete_service_account(account.id)


async def main() -> None:
    try:
        await run_check(None, "open (dev)")
    except BaseException as exc:  # ExceptionGroup from the transport on 401
        if not is_unauthorized(exc):
            raise
        await run_check_with_probe_pat()


asyncio.run(main())
PY
then
    echo ""
    echo -e "${BOLD}Done.${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}${BOLD}Failed.${NC} ${DIM}Check the container: docker compose logs agentos-api${NC}"
    echo ""
    exit 1
fi
