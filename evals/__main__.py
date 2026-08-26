"""
Run Evals
=========

python -m evals                         # run all cases (concise UI)
python -m evals --tag smoke             # run a tagged subset
python -m evals --name <case>           # run one case
python -m evals --tag smoke --list      # show what a tag selects, spending nothing
python -m evals --timeout 180           # per-case clock for cases that set none (120s)
python -m evals --json-output out.json  # write machine-readable results
python -m evals -v                      # stream the agent's run with full panels

Agno's eval runner runs each case and evaluates the response with `AgentAsJudgeEval`
(when `criteria` is set) and/or `ReliabilityEval` (when `expected_tool_calls` is set).

Exit code 0 means every selected case passed, 1 means one failed (or a `--json-output`
write did), and 2 means the selector matched nothing — so a mistyped `--tag` fails a CI
gate rather than greening it on an empty run.

Both log to Postgres through `eval_db`. Connect your AgentOS at os.agno.com to see history.
"""

# Hydrate os.environ from .env before any module that reads env at import time
# (db_url, model factories, etc.). Pre-existing shell vars take precedence.
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import asyncio  # noqa: E402
import sys  # noqa: E402

from agno.eval.suite import acli  # noqa: E402
from agno.os.utils import collect_mcp_tools_from_registry  # noqa: E402
from agno.utils.log import log_warning  # noqa: E402

from app.registry import registry  # noqa: E402
from evals.cases import CASES, eval_db  # noqa: E402


def _is_mcp_tool(tool: object) -> bool:
    return hasattr(type(tool), "__mro__") and any(c.__name__ == "MCPTools" for c in type(tool).__mro__)


def _mcp_tools_under_test() -> list:
    """Every MCP toolkit a run in this suite could touch: the ones declared on the
    registry (Studio-built components serialize *their* functions at persist time) plus
    the ones attached to the agents/teams the cases probe.
    """
    tools: list = []
    collect_mcp_tools_from_registry(registry, tools)
    for case in CASES:
        component = getattr(case, "agent", None) or getattr(case, "team", None)
        component_tools = getattr(component, "tools", None)
        if isinstance(component_tools, list):
            for tool in component_tools:
                if _is_mcp_tool(tool) and tool not in tools:
                    tools.append(tool)
    return tools


async def _run() -> int:
    # AgentOS connects these MCP toolkits in its server lifespan; `python -m evals` is a
    # standalone process with no lifespan, so without this the registry's `parallel_tools`
    # (and `agno_docs`) stay unconnected and expose no functions — a Platform Builder case
    # that wires web search then fails at persist time ("toolkit exposes no functions"),
    # even though the same build succeeds against the running server. Connect them in this
    # loop (the one the cases run in — MCP sessions are event-loop-bound), then close them.
    connected: list = []
    for tool in _mcp_tools_under_test():
        try:
            await tool.connect()
            connected.append(tool)
        except Exception as exc:  # a flaky/unreachable MCP host must not sink the whole suite
            log_warning(f"eval setup: could not connect MCP tool {getattr(tool, 'name', tool)!r}: {exc}")
    try:
        return await acli(CASES, db=eval_db)
    finally:
        for tool in connected:
            try:
                await tool.close()
            except Exception:
                pass


# Behind the guard so an import never spends money: `python -m evals` still runs this
# (the -m form sets __name__ to "__main__"), while an import sweep, an IDE indexer
# or a docs tool that reaches this module gets a no-op instead of a live suite run.
if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
