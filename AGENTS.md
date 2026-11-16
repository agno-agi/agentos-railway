# AgentOS Railway template

This is a thin application over Agno. Application wiring and policy live here. Super Agent
(`superagent`), Platform Builder, Studio, authorization, the durable queue and sandbox
lifecycle belong in the Agno SDK. `CLAUDE.md` links to this file.

## Working rules

- Read the relevant source and `git status` before editing. Keep unrelated changes and stay
  within the requested scope.
- Do not recreate framework components or work around a framework rejection. Check behavior
  against the Agno version pinned in `pyproject.toml`.
- Keep the template lean. Add abstractions, tests and infrastructure only for a concrete need.
- Never print or commit credentials.

## Skills

Read the matching skill in `.agents/skills/` before starting; `.claude/skills` links there.

| Task | Skill |
| --- | --- |
| First local setup | [setup-platform](.agents/skills/setup-platform/SKILL.md) |
| Add an agent | [create-agent](.agents/skills/create-agent/SKILL.md) |
| Change an agent or add a Studio capability | [extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Add eval coverage | [create-evals](.agents/skills/create-evals/SKILL.md) |
| Harden an agent with simulations and targeted fixes | [improve](.agents/skills/improve/SKILL.md) |
| Review repository consistency and public readiness | [review-and-improve](.agents/skills/review-and-improve/SKILL.md) |
| Deploy or change production configuration | [deploy-platform](.agents/skills/deploy-platform/SKILL.md) |

## Layout

| Path | What it holds |
| --- | --- |
| `app/main.py` | The AgentOS: database, Super Agent, Company, queue and registered agents. |
| `app/company.py` | Product, Source and Routine declarations. |
| `app/config.yaml` | Descriptions and quick prompts shown in the UI. Every quick prompt is ten words or fewer. |
| `app/registry.py` | What Studio can build with, plus web tools, shared knowledge, learning and notes. |
| `app/settings.py` | Model factories. |
| `app/interfaces.py` | MCP tools and OAuth; optional Slack. |
| `app/sandbox.py` | Sandbox switch, provider, repository and checkpoints. |
| `agents/` | Application agents, including the Claude and Codex coding agents. |
| `db/` | The shared PostgreSQL database and knowledge creation. |
| `evals/` | Eval cases and the CLI entrypoint. |
| `scripts/` | Setup, validation, image build and the AWS sandbox helper. |
| `compose.yaml`, `Dockerfile`, `railway.json`, `scripts/railway/` | Local stack, API and sandbox images, provider deployment configuration. |

## Develop

Run commands from the repository root.

```sh
cp example.env .env            # only if .env is missing; set OPENAI_API_KEY
docker compose up -d --build   # API on http://localhost:8000, no JWT in development
./scripts/venv_setup.sh && source .venv/bin/activate
./scripts/format.sh
./scripts/validate.sh          # ruff and mypy; CI runs the same script
```

Dependencies are declared in `pyproject.toml`. After changing them, run
`./scripts/generate_requirements.sh` and rebuild both Dockerfile targets. Do not add `uv.lock`.

## Agents and storage

- Follow the agent shape in `create-agent`. Register code agents in `app/main.py` and describe
  them in `app/config.yaml`.
- Everything shares one database: call `get_postgres_db()` with no arguments. Create a
  knowledge base with `create_knowledge()` so it gets its own contents store.
- Shared resources come from `app/registry.py`: `shared_knowledge` (operator documents),
  `shared_learning` (per-user profiles and memories) and `shared_notes.tools()` (a notebook in
  PostgreSQL). Company knowledge belongs in the Company wiki.

## Company

- `app/company.py` declares the `AgentOS` Product and its `agentos-maintenance` Routine:
  Mondays at 09:00 UTC, disabled by default, proposing work and accepting nothing.
  It is enabled from the Company page in the AgentOS UI, and each run spends model calls.
- Declarations seed the database once. Saved Products, Sources and Routines keep later edits,
  so change saved records through the UI or API, not only in code.
- Leave Routine executors unset to use Agno's default. Explicit executors must be registered
  application agents, teams or workflows.
- Assign sandboxed coding Tasks explicitly to Claude Engineer or Codex Engineer.

## Coding agents and sandboxes

Setup is in [docs/harnesses.md](docs/harnesses.md). When changing this code:

- Claude Engineer and Codex Engineer are declared in `agents/engineers.py` and stay off until
  their factories are enabled in `app/main.py`. Keep their IDs.
- Without a sandbox they run in the project root on the API host. With `SANDBOX_ENABLED = True`
  in `app/sandbox.py` they run in a sandbox with their own checkout of `REPOSITORY`, which
  must be set.
- `SANDBOX_PROVIDER` selects `docker` (local) or `agentcore` (hosted). A wrong provider or
  missing AgentCore settings must stop startup, never fall back to running on the host.
- The Docker socket mount is off by default. Enable it only for local Docker sandboxes,
  in the API container; sandboxes must not receive it.
- Runtime ARNs, buckets and tokens come from the environment and are never committed.
  Checkpoints go to `tmp/checkpoints` locally and S3 when hosted, not PostgreSQL.
- Company declares a Git Source for `REPOSITORY` when it is set. Keep the two the same;
  sandboxed Company Tasks need a saved Git Source that matches `REPOSITORY.url`.

## Production

The deployment target is Railway, through `railway.json`, `scripts/railway/` and the
[deploy-platform](.agents/skills/deploy-platform/SKILL.md) skill. Follow the
[production setup](README.md#deploy-in-production). Run one API instance with persistent
PostgreSQL; read [docs/scaling.md](docs/scaling.md) before adding replicas.
Keep production authorization enabled (`RUNTIME_ENV=prd`); the verification key must be
configured before the API can start. Preserve provider settings and existing database data.

Removing a declaration does not remove saved records. Before renaming or removing a
component, check saved schedules and Studio references, and keep existing sessions, notes and
Company work.

## Verification

| Check | What it shows |
| --- | --- |
| `./scripts/validate.sh` and `git diff --check` | Formatting, lint and types. |
| `./scripts/mcp_check.sh` | MCP handshake and required tools, without a model call. |
| `python -m evals --tag smoke` | Three Super Agent cases. Spends model calls, needs PostgreSQL and saves results. |

A running API does not show that agents, coding agents or Company Tasks work; run them.
Local checks do not show that a deployment works. Record what you checked in `tmp/VERIFY.md`.
Keep evals in `evals/cases.py` with Agno's `criteria` and `expected_tool_calls`; do not add
custom scoring or cleanup machinery.
