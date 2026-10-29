"""Claude and Codex agents for engineering tasks."""

from pathlib import Path

from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent

from app.sandbox import REPOSITORY, sandbox_provider
from db import get_postgres_db

db = get_postgres_db()
sandbox = sandbox_provider()
if sandbox is not None and REPOSITORY is None:
    raise ValueError("Set REPOSITORY in app/sandbox.py before enabling a sandbox.")
repository = None if sandbox is None else REPOSITORY
cwd = str(Path(__file__).resolve().parents[1]) if sandbox is None else None


def create_claude_engineer() -> ClaudeAgent:
    return ClaudeAgent(
        id="claude-engineer",
        name="Claude Engineer",
        model="claude-opus-5-5",
        db=db,
        cwd=cwd,
        sandbox=sandbox,
        repository=repository,
        system_prompt={"type": "preset", "preset": "claude_code"},
        permission_mode="acceptEdits",
    )


def create_codex_engineer() -> CodexAgent:
    return CodexAgent(
        id="codex-engineer",
        name="Codex Engineer",
        model="gpt-6.1-sol",
        db=db,
        cwd=cwd,
        sandbox=sandbox,
        repository=repository,
        sandbox_mode="workspace-write",
    )
