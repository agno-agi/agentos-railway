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

import sys  # noqa: E402

from agno.eval import cli  # noqa: E402

from evals.cases import CASES, eval_db  # noqa: E402

sys.exit(cli(CASES, db=eval_db))
