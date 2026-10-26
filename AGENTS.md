# AgentOS Railway template

This is a thin application over Agno. Keep application wiring and policy here;
generic manager behavior belongs in Agno. `CLAUDE.md` links to this file.

## Working rules

- Read the relevant source and inspect `git status` before editing. Preserve unrelated
  changes and keep work within the requested scope.
- Agno owns OS Manager (`os-manager-internal`), its members, source tools, Studio,
  Company Manager (`company-manager-internal`), authorization, durable execution and sandbox lifecycle.
  Configure `OSManager(root=agentos_root)` in `app/main.py`; do not recreate these components
  or add application-owned queues, lifecycle code or Company state machines.
- Check framework behavior against the Agno version pinned in `pyproject.toml`.
  Do not bypass framework rejections or add compatibility adapters to this template.
- Keep the starter lean. Add abstractions, tests and infrastructure only for a concrete
  application need. Never print or commit credentials.

## Workflows

Read the relevant local skill before starting. Slash commands refer to coding-agent
workflows in `.agents/skills/`; `.claude/skills` links to that directory.

| Task | Skill |
| --- | --- |
| First local setup | [setup-platform](.agents/skills/setup-platform/SKILL.md) |
| Add an agent | [create-agent](.agents/skills/create-agent/SKILL.md) |
| Change an agent or add a Studio capability | [extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Add behavioral coverage | [create-evals](.agents/skills/create-evals/SKILL.md) |
| Repair evals or explore and improve agent behavior | [improve](.agents/skills/improve/SKILL.md) |
| Review repository consistency and public readiness | [review-and-improve](.agents/skills/review-and-improve/SKILL.md) |
| Deploy or change production configuration | [deploy-platform](.agents/skills/deploy-platform/SKILL.md) |

## Where changes belong

- `app/main.py`: AgentOS registration, shared database, OS Manager, Company and queue.
- `app/interfaces.py`: MCP OAuth, `os_manager` and built-in MCP tools, optional Slack.
- `app/company.py`: Product and Source declarations. `app/config.yaml`: component
  descriptions, prompts and optional additional Products.
- `app/registry.py`: Studio palette, web tools, shared knowledge, learning and notes.
  `app/settings.py`: application model factories.
- `app/sandbox.py`: providers, repository URL/branch and checkpoint paths.
- `agents/`: application agents, including the Claude and Codex engineers.
  `teams/`: user-defined teams; no Engineering team ships by default.
- `db/`: cached OS database and distinct knowledge content adapters.
- `evals/`: application cases and the Agno eval CLI entrypoint.
- `scripts/`: setup, validation and image builds. `scripts/railway/deploy.py` is the
  shared implementation for production provisioning, env sync, redeploy and teardown.
- `compose.yaml`: local PostgreSQL and development API. `railway.json`: single-replica
  production deployment. `Dockerfile`: shared dependencies for `agentos` (default)
  and `sandbox` targets. No Redis ships with this template.

## Local development

Run commands from the repository root. Copy `example.env` to `.env` only if absent,
set `OPENAI_API_KEY`, then use `docker compose up -d --build`. Compose exposes ports
on loopback and disables JWT for development; application code defaults to `prd`.

For Python development:

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
./scripts/format.sh
./scripts/validate.sh
```

`pyproject.toml` declares dependencies. Regenerate `requirements.txt` with
`./scripts/generate_requirements.sh`; do not add `uv.lock`. Use `uv run --no-project`
outside the activated environment. Both Dockerfile targets install the same pinned
requirements; rebuild both after dependency changes.

## Agents and storage

Follow the Agent shape in `create-agent`: stable ID, explicit instructions/tools,
`default_model()`, shared DB, history and datetime. Register code agents and teams in
`app/main.py` and their descriptions/prompts in `app/config.yaml`. Put new Studio
capabilities in `app/registry.py`; import shared resources from there.

OS, Company, queue, agents and teams must reuse `get_postgres_db()` with no arguments.
Knowledge content adapters need distinct IDs; never create a second adapter with the OS ID.

- `shared_knowledge`: operator documents.
- `shared_learning`: per-user profiles and memories; attach when an agent should remember users.
- `shared_notes.tools()`: a PostgreSQL notebook with read/write, append, replace, list,
  search and move tools. User scoping follows AgentOS user isolation.
- Company wiki: Company knowledge.
- Product agents: declare a separate knowledge base on demand; do not use operator
  documents or shared notes as their product knowledge.

Company Products contain Projects and Routines; Tasks belong to Projects. On the current
pin, Product metadata PATCH replaces the whole dictionary. Preserve existing metadata.
`app/company.py` declares `agentos-maintenance` for every day at 09:00 UTC, executed by
Company Manager (`company-manager-internal`, executor type `agent`). It reviews Agno
releases and this codebase and proposes up to three Backlog Tasks, reusing existing
proposals. Its instructions prohibit accepting or executing work; `auto_accept=False`.
Scheduled reviews spend model calls. Verify the saved creator, schedule, authorization
and run history before relying on them; declarations do not overwrite saved edits.

Company writes are governed by permission scopes, not record ownership; `user_id`
records the creator. Task run sessions retain their ownership checks. Manual triggers
for auto-accept Routines require the acceptance grantor.

The current pin permits Company Manager as a Routine executor; OS Manager and its
specialists remain excluded. Before adding a Routine, verify executor support and
the caller's authorization. Do not register internal manager members to bypass
executor restrictions.

## Engineers and sandboxes

Keep the engineers' stable IDs and explicit models. Both are registered and run in the
absolute project root on the AgentOS server when no sandbox is configured. A configured
sandbox owns its repository checkout; invalid configuration must fail rather than fall
back to server execution. Keep provider configuration in `app/sandbox.py` and agent
declarations in `agents/engineers.py`.

Select the provider by returning `None`, `docker_sandbox()`, or
`agentcore_sandbox("runtime-arn", "checkpoint-bucket")` from `sandbox_provider()`. Sandbox selection, image
and runtime ARN are code settings, not environment switches. Supply optional Bedrock
settings or private-repository credentials explicitly through the provider's `env`;
never put credential values in source. Agno forwards the harness model credentials.

For Docker engineering, run the API on the host using the [sandbox setup guide](docs/sandboxes.md#local-docker-sandbox).
Build the sandbox with `docker build --target sandbox --load -t agno-sandbox:local .`.
Development checkpoints use the absolute project `tmp/checkpoints` path and survive
only while those files remain. Hosted AgentCore checkpoints use S3; no API disk is
required. Configure the bucket/prefix explicitly and give the API appropriate AWS
access, following docs/sandboxes.md. Do not put checkpoint archives in PostgreSQL.
See [docs/scaling.md](docs/scaling.md) for current scaling guidance.
Local source mounts and PostgreSQL volumes remain.

`REPOSITORY` in `app/sandbox.py` defaults to `None`. Set it to a `Repository` with
the user's URL and branch before enabling a sandbox; startup rejects a sandbox
without a repository. Direct server execution does not need one. Company always
declares the local readable Source and only declares a remote Git Source when
`REPOSITORY` is set. Company sandbox acceptance requires a saved Product Git Source
matching `REPOSITORY.url`; retain the local readable Source.
New Source declarations are seeded without replacing saved edits. The pinned framework
supports sandbox HTTP admission through the durable PostgreSQL queue with session ordering.

## Production and saved state

Use the deployment skill and [Railway instructions](README.md#deploy-on-railway).
Commands use the project venv, Railway CLI 5.49.0 or newer, and an explicit production
env file (default `.env.production`). Never sync `RUNTIME_ENV=dev` to production.
Start with one API instance and require JWT verification before deploying the API.
Follow docs/scaling.md when adding replicas.

Provisioning requires a workspace and rejects an already-linked checkout. Use env sync
and redeploy for an existing project. Keep application policy in `app/`, environment
settings in env files, local services in Compose and production settings in `railway.json`.

Before removing or renaming components in an existing deployment, inspect saved schedules
and Studio references. Removing a declaration does not remove persisted records. Preserve
historical sessions, notes and Company work; migrate saved references deliberately.

## Verification

`./scripts/validate.sh` checks formatting, lint and types; CI uses the same command.
Also run `git diff --check`. Keep evals in `evals/__main__.py` and `evals/cases.py`, using
Agno's `criteria` and `expected_tool_calls`. Do not add a bundled regression suite or
custom isolation, scorers or cleanup machinery by default.

- `python -m evals --tag smoke`: runs the three application cases and spends model calls.
  Uses the application's `.env`, database and workspace; sessions and results persist
  for the AgentOS UI. The CLI defaults to `dev` unless configured otherwise and does not
  start the API or scheduler. Even `--help` and `--list` require PostgreSQL because the
  application initializes knowledge storage on import.
- Inspect answers, tool results and judge reasons. Additional tool calls are allowed;
  these cases do not enforce read-only execution. Use owned fixtures for mutating cases.
- `./scripts/mcp_check.sh`: initializes MCP and checks required tools without model calls.
  `--prompt` spends model calls. Set `MCP_CHECK_HOST=1` for the host API.
- Verify direct engineer execution, HTTP execution, team delegation and Company Task
  acceptance/completion separately. API startup does not establish these capabilities.

Record checks and limits in `tmp/VERIFY.md`, separating static, deterministic, model,
container and hosted results. Do not infer deployed readiness from local checks.
