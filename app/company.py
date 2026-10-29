"""
CompanyOS
=========
"""

from pathlib import Path

from agno.company import Product, Routine, Source

from app.sandbox import REPOSITORY

MAINTENANCE = """\
Create Projects and Tasks to improve this AgentOS. Read the Product context, existing work
and AGENTS.md, then review Agno releases since the pinned version and this codebase.
Look for useful SDK capabilities, bugs, stale configuration and opportunities to simplify.
Propose up to three high-value improvements as Backlog Tasks in suitable Projects.
For each, cite source evidence and explain what should change, why it matters and how
to verify it. Reuse existing proposals instead of creating duplicates.
Do not accept or execute work. If nothing is worth changing, create no work.
"""

products = [
    Product(
        id="this-agentos",
        name="AgentOS",
        purpose="Improve this AgentOS by scanning this codebase and agno releases.",
        sources=[
            Source(type="website", reference="https://github.com/agno-agi/agno/releases"),
            Source(type="git", reference=str(Path(__file__).resolve().parents[1])),
            *([Source(type="git", reference=REPOSITORY.url)] if REPOSITORY is not None else []),
        ],
        routines=[
            Routine(
                name="agentos-maintenance",
                executor_type="agent",
                executor_id="company-manager-internal",
                cron_expr="0 9 * * *",
                instructions=MAINTENANCE,
                enabled=False,
                auto_accept=False,
            ),
        ],
    ),
]
