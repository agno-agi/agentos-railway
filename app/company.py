"""
CompanyOS
=========
"""

from pathlib import Path

from agno.company import Product, Routine, Source

from app.sandbox import REPOSITORY

# Recommended: enable an engineer in app/main.py, then add a line to these instructions
# naming it as the executor for code changes, for example: "Use codex-engineer for code changes."
MAINTENANCE = """\
Keep this AgentOS current, secure and working. Propose only demonstrated problems or
released Agno changes affecting this repository. No new features, tables or refactors.
Most runs should propose nothing.

Read AGENTS.md, the Product status and open Projects and Tasks. Resume unfinished
checks, then scan upgrades, security and quality. Stay within this Product; skip the
company wiki. You have 30 tool calls: reserve the last 3 for updating status.

- Upgrades: compare the Agno pin with newer releases; propose relevant upgrades with
  breaking changes and required checks.
- Security: exposed secrets, weakened authorization, unnecessary tools and dependency
  advisories.
- Quality: conflicting instructions or configuration, ineffective settings and missing
  or failing checks.

Resolve code/docs disagreements using Product context, decisions, tests and history.
Never rewrite docs to excuse weakened protections or tests. Record unclear decisions
in Product status for a person; do not guess.

Propose one bounded Project per finding, named for its outcome, with one Task per PR.
Reuse existing Projects. Cite file/line or release-note evidence, explain the change
and why it matters, and say how to verify it.

Always update Product status before the tool limit: date, latest Agno release reviewed,
checks completed and what to check next, even if the scan is incomplete.
"""

products = [
    Product(
        id="this-agentos",
        name="AgentOS",
        purpose="Keep this AgentOS current, secure and working.",
        sources=[
            Source(type="website", reference="https://github.com/agno-agi/agno/releases"),
            Source(type="git", reference=str(Path(__file__).resolve().parents[1])),
            *([Source(type="git", reference=REPOSITORY.url)] if REPOSITORY is not None else []),
        ],
        routines=[
            # This routine runs on Agno's default routine executor: `miniagent`.
            Routine(
                name="agentos-maintenance",
                # Mondays at 09:00 UTC.
                cron_expr="0 9 * * 1",
                instructions=MAINTENANCE,
                enabled=False,
                auto_accept=False,
            ),
        ],
    ),
]
