# AgentOS

Build agents and serve them through an API, MCP clients, and optional Slack with
[Agno](https://github.com/agno-agi/agno). Use a coding agent, ask OS Manager to build
components, or compose them in AgentOS Studio. Sessions, learning and Company work
live in PostgreSQL.

This template provides application wiring and configuration. Agno owns OS Manager,
Company Manager, Studio, authorization, durable execution and sandbox lifecycle.

## Get started

Give your coding agent this prompt:

```text
Help me set up my agent platform and build my first agent.
Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

Already have a checkout? Run [/setup-platform](.agents/skills/setup-platform/SKILL.md)
in your coding agent. It guides local setup, connects the UI and helps build your first
agent. To set things up yourself, follow the steps below.

## Run locally

Requires Git, Docker with Compose, and an OpenAI API key. Start Docker, then clone
and enter the repository (skip this if you already have a checkout):

```sh
git clone https://github.com/agno-agi/agentos-railway agent-platform
cd agent-platform
```

Run the remaining commands from the repository root. Copy the environment file only
if absent, then open `.env` in your editor and set `OPENAI_API_KEY`:

```sh
[ -f .env ] || cp example.env .env
```

Start the platform, wait for the API, and check MCP:

```sh
docker compose up -d --build && \
curl --fail --silent --show-error --retry 30 --retry-connrefused \
  --retry-delay 2 --retry-max-time 120 --max-time 5 http://localhost:8000/health \
  && ./scripts/mcp_check.sh
```

If the readiness check fails, inspect `docker compose logs agentos-api agentos-db`
before retrying.

The MCP check initializes the connection and verifies the required tools without a model
call. Supply a prompt to also test OS Manager (spends model calls):

```sh
./scripts/mcp_check.sh --prompt "Without using tools, introduce yourself briefly."
```

Open [AgentOS](https://os.agno.com), sign in, and choose **Connect OS**. Select a local
connection, enter `http://localhost:8000`, and name it **Local AgentOS**. Open the chat
for **OS Manager**.

Its HTTP route is `/teams/os-manager-internal/runs`; its MCP tool is `agno` at `/mcp`.
The eight built-in MCP tools remain available alongside `agno`.
Set both Slack credentials to enable the Slack interface.

Local development disables JWT; production requires verification. Never copy
`RUNTIME_ENV=dev` into an environment file that will sync to production.
Compose publishes the API and database on loopback only. This template runs one
API replica with a PostgreSQL durable queue and no Redis.

## Build agents

For your first agent, ask OS Manager:

> Help me build an agent for my product. I'll give you its documentation URL and
> explain what users should be able to ask it.

Review the proposed behavior, then ask it to build and publish the agent. Refresh the
UI's Agents list and try a question with a known answer. You can also use Studio to
compose a component, or run [/create-agent](.agents/skills/create-agent/SKILL.md) in
your coding agent to add a Python agent to this repository.

The coding-agent workflows cover the rest of the lifecycle:

| Task | Skill |
| --- | --- |
| Add an agent | [/create-agent](.agents/skills/create-agent/SKILL.md) |
| Add a capability or fix a known issue | [/extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Add behavioral coverage | [/create-evals](.agents/skills/create-evals/SKILL.md) |
| Repair evals or explore simulated user scenarios | [/eval-and-improve](.agents/skills/eval-and-improve/SKILL.md) |
| Review repository consistency before sharing | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

OS Manager and Studio compose components from [app/registry.py](app/registry.py).
The palette contains web access, lightweight file generation, a calculator, models,
learning, knowledge, and shared notes. New runtime capabilities enter this explicit registry.

Import `shared_knowledge`, `shared_learning`, and `shared_notes` from `app.registry`.
Operator documents use shared knowledge; learning stores per-user profiles and memories.
Attach `shared_notes.tools()` for a PostgreSQL notebook. Its default tools can read, write,
append, replace, list, search and move notes. User scoping follows AgentOS user isolation.
Keep personal profiles in learning and Company knowledge in Company wiki.
Create a separate knowledge base when adding an end-user product agent; none ships by default.
Existing product-knowledge data is preserved, but saved Studio components referencing it need
their knowledge declaration restored or their configuration updated before deployment.
Register code agents and teams in `app/main.py` and add their
prompts to `app/config.yaml`. No example workflows ship by default. Company uses the
framework scheduler for its [maintenance Routine](#company).

## Make it yours

Create an empty private repository on GitHub. For a fresh clone whose `origin` still
points to this template, replace the URL below with your repository URL:

```sh
git remote rename origin upstream
git remote add origin https://github.com/YOUR-ORG/YOUR-REPO.git
git push -u origin HEAD
```

The template remains available as `upstream`; review updates before merging them.
For sandbox engineering, also update `REPOSITORY` in `app/sandbox.py` to your repository
and branch. Existing deployments need their saved Product Sources checked too; see
[Company](#company).

## Verify and develop

Install [uv](https://docs.astral.sh/uv/) for host development, evals and Railway scripts.
The setup script creates a Python 3.14 environment and installs dependencies. If a venv
is already active, run `deactivate` before running setup again.

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
./scripts/format.sh
./scripts/validate.sh
python -m evals --tag smoke --json-output tmp/evals.json
```

Model evals use the application's `.env`, database and workspace and spend model calls.
The CLI defaults to development mode unless `RUNTIME_ENV` is explicitly configured.
Sessions and eval results persist in the configured database for the AgentOS UI.
The CLI does not start the API server or scheduler.

The three cases in [evals/cases.py](evals/cases.py) check onboarding, diagnostics and
the application's learning configuration. They use Agno's built-in answer criteria
and expected tool-call checks. These behavioral checks allow additional tool calls;
they do not enforce the prompts' read-only instructions. Add application cases here;
generic manager and Company behavior belongs in Agno's coverage. `--json-output` saves
Agno's report (answers, tool names and verdicts). Use `--name <case>` to select one case or `--list`
to inspect the suite without model calls. The CLI imports the application, so PostgreSQL
must be running even for `--help` and `--list`.

Dependencies flow from `pyproject.toml` through `scripts/generate_requirements.sh` to
committed `requirements.txt`. Docker, CI and host setup use those requirements. There
is no `uv.lock`; use `uv run --no-project` when invoking uv outside the activated venv.
After changing dependencies, regenerate requirements and rebuild both Dockerfile targets.

The root [Dockerfile](Dockerfile) has two targets sharing the same pinned dependencies:
`agentos` serves the API and is the default for Railway and Compose; `sandbox` starts the
execution runtime and does not copy application code. Build the API locally with
`docker build --target agentos --load -t agentos:local .`. Both builds use the root
`.dockerignore` to exclude local credentials, caches and working data.

## Deploy on Railway

Install Railway CLI **5.49.0 or newer** and run `railway login`. The deployment scripts
use the project venv; if it is not set up yet, install uv and follow
[Verify and develop](#verify-and-develop) through environment setup.
Use [/deploy-platform](.agents/skills/deploy-platform/SKILL.md) for the guided path, or
copy `example.env` to `.env.production` only if absent, set its keys, then run:

```sh
./scripts/railway/up.sh --workspace <workspace-name-or-id>
```

The four shell entrypoints use one implementation in `scripts/railway/deploy.py`.
Provisioning and environment updates parse the same production file and upload all its
variables without printing values or triggering a deployment per variable. Values use
dotenv quoting, including quoted multiline PEMs; shell commands and `${...}` references
are not evaluated. `.env` and exported application variables are not loaded implicitly.
Pass an explicit env-file path to `up.sh` or `env-sync.sh` to use a different file.

First provisioning creates the API and pgvector services, database volume and public
domain. It saves the managed database settings, a generated database password when absent,
and an MCP connect secret in the production file. `RAILWAY_WORKSPACE` is an alternative
to `--workspace`. An already-linked checkout is rejected: service health is never used
to decide whether to create another project.

If JWT verification is missing, provisioning exits **2** after saving the URL and settings;
the API is not deployed. The provisioned resources are billed. Connect the URL at
os.agno.com, enable token-based authorization, and save the public verification key in
the same file. Finish with `env-sync.sh --no-deploy`, then `redeploy.sh`.
Both provisioning and env sync reject development mode. Keep the MCP connect secret in
the file and enter it in the connector consent page; deployment logs do not print it.

```sh
./scripts/railway/redeploy.sh   # changed code
./scripts/railway/env-sync.sh   # changed production settings
railway logs --service agent-os
./scripts/railway/down.sh      # deletes the project, database and all its data
```

When changing both code and settings, run `env-sync.sh --no-deploy` before `redeploy.sh`.
An upload failure stops before deployment; some earlier variables may already have changed,
so correct the file and rerun the sync. Removing a line does not delete a remote variable:
set optional credentials or the sandbox ARN to empty to disable them, or remove them
explicitly through Railway.
Database credential changes require a separate PostgreSQL rotation; env sync updates the API.
Teardown verifies project deletion before unlinking and preserves local env files.
Review the saved URL and JWT settings before provisioning another project.

Build submission is not a readiness check. Inspect logs, verify `/health`, confirm
unauthenticated `/agents` requests and MCP initialization POSTs are rejected, and
exercise an authenticated request before sharing. A plain `GET /mcp` can serve
public discovery metadata and is not an authorization check.

For browser MCP clients, connect to `https://<domain>/mcp` using OAuth and the configured
`MCP_CONNECT_SECRET`. Coding clients can use `uvx agno connect --url https://<domain>`.
For the authenticated MCP probe, provide an existing JWT or PAT as `MCP_CHECK_TOKEN`;
the check does not mint accounts.

When upgrading an existing deployment, disable its old `deployment-check` and
`run-evals` schedules before removing those endpoints. Inspect saved Studio components
for references to removed functions/toolkits. Migrate references deliberately; do not delete historical state.

## Company

The **AgentOS** Product in [app/company.py](app/company.py) represents this deployment:
useful agents, reliable execution and continuous improvement. Its Sources are Agno
release notes and the application source. Agno's Company Manager handles planning,
evidence-backed proposals and status updates through OS Manager.
The Product also declares the repository URL from `app/sandbox.py`, which Company
uses to admit sandboxed engineering Tasks. Keep the local source for reading files.

Ask OS Manager to review relevant releases and recommend the next improvement.
The declared `agentos-maintenance` Routine runs on Mondays at 09:00 UTC using Company
Manager. It is instructed to review Agno releases and the repository, propose up to three
Tasks in Backlog, and leave acceptance and execution to human review. Automatic acceptance
is disabled. Scheduled reviews spend model calls; verify the Product's saved ownership,
the schedule and its run history before relying on them.

The pinned framework supports Company Manager (`company-manager-internal`, executor type
`agent`) as a Routine executor; OS Manager and its specialists remain excluded. Before
scheduling work, verify the caller's authorization. Do not register internal manager
members to bypass executor restrictions.

Declarations seed new records without overwriting saved edits. Before upgrading an
existing deployment, update the Product's saved name/purpose and disable or retarget
saved schedules using the removed `company-analyst`, including Release intake,
Daily refresh, Weekly summary and Weekly review. Inspect saved Studio references too.
The Product ID remains `this-agentos`. Removing declarations does not delete saved
Routines or historical work. `ENABLE_MAINTENANCE` is no longer used.
Agno seeds newly declared Sources on startup without overwriting existing ones.
After changing the repository for a fork, inspect the saved Product Sources: its Git
URL must match `REPOSITORY.url` before accepting sandbox Tasks. Retire obsolete
sources deliberately; do not delete historical work.

Declare additional Products in `app/company.py` or under `company.products` in
`app/config.yaml`. On the current dependency pin, Product metadata PATCH replaces
the dictionary; include all metadata when editing it.

## Engineers

[agents/engineers.py](agents/engineers.py) declares two independent coding agents:

| Agent | Harness | Default model |
| --- | --- | --- |
| Claude Engineer (`claude-engineer`) | Claude Code | `claude-opus-5-5` |
| Codex Engineer (`codex-engineer`) | Codex | `gpt-6.1-sol` |

Models are defined directly in `agents/engineers.py`; edit their `model` arguments to change them.
Both agents are always registered. Without a sandbox, their harnesses run on the
AgentOS server in the absolute project root (`/app` in the API container). With a sandbox
configured, they run in its repository checkout. Invalid sandbox configuration fails
at startup rather than falling back to the server. `RUNTIME_ENV` accepts only `dev`
or `prd`, and `SANDBOX_ENABLED` accepts only `true` or `false`. An AgentCore ARN is
production-only; enabling Docker in production is rejected. Claude on AgentCore uses
Bedrock; set Claude's `model` argument to an inference profile supported by that account. An
Engineering team is deferred until framework support and delegation have been tested.

For local Docker sandboxes, run the API on the host so it can reach the Docker daemon.
Install [uv](https://docs.astral.sh/uv/) first and configure `.env` as in [Run locally](#run-locally).
If a venv is active, run `deactivate` before the setup script:

```sh
docker compose up -d agentos-db
./scripts/venv_setup.sh
docker build --target sandbox --load -t agno-sandbox:local .
docker image inspect agno-sandbox:local --format '{{.Id}}'
docker compose stop agentos-api
RUNTIME_ENV=dev DB_HOST=127.0.0.1 DB_PORT=5432 SANDBOX_ENABLED=true \
  AGENTOS_URL=http://127.0.0.1:8000 \
  uv run --no-project --env-file .env --with-requirements requirements.txt \
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload \
  --reload-dir agents --reload-dir app --reload-dir db --reload-dir evals
# From another terminal:
MCP_CHECK_HOST=1 ./scripts/mcp_check.sh
```

Repository configuration, provider selection and checkpoints live in
[app/sandbox.py](app/sandbox.py). Edit `REPOSITORY` for your fork; it defaults to this
template's GitHub repository on `main`. Development checkpoints use the absolute project
`tmp/checkpoints` directory. Server-hosted or local Claude needs `ANTHROPIC_API_KEY`; Codex uses
`OPENAI_API_KEY`. Private repository cloning can use `GITHUB_READ_TOKEN`, which enters
the sandbox. Publication credentials are not configured by this template.

The pinned framework admits sandboxed HTTP runs through a durable queue with session
ordering; the shared PostgreSQL database supplies that capability. Redis is not required
for this single-replica configuration. API startup alone does not verify execution:
check an engineer HTTP run and Company Task acceptance/completion separately.
Direct Python harness execution and team delegation are separate verification paths.

Production uses AgentCore, an ARM64 runtime image, and a persistent checkpoint volume.
The API does not need a Docker daemon. Build an ARM64 image with:

```sh
# Set SANDBOX_IMAGE to your ECR URI with an immutable tag.
docker build --target sandbox --platform linux/arm64 --load -t "${SANDBOX_IMAGE}" .
docker image inspect "${SANDBOX_IMAGE}" --format '{{.Id}}'
```

Push the image to ECR and provision the AgentCore runtime and its execution role through
your AWS tooling. The host AgentCore client uses the region encoded in the runtime ARN.
`AWS_REGION` is forwarded into the sandbox for Claude/Bedrock and defaults to `us-east-1`;
set it for the region where your chosen inference profile is available.
Set `SANDBOX_RUNTIME_ARN` to that runtime's ARN; checkpoints use
`/data/checkpoints`. First-time Railway provisioning adds the `/data` volume when the ARN
is configured. When enabling AgentCore on an existing deployment, mount that volume before
syncing the ARN. Startup rejects AgentCore without the mount. Keep one API replica.
Company sandbox integration exists in the pin, but its repository/source contract and
acceptance/completion still need verification on your deployment.

## Configuration

See [example.env](example.env) for copyable settings. No real credentials belong in Git.

| Setting | Purpose / default |
| --- | --- |
| `OPENAI_API_KEY` | Application model, embeddings and Codex authentication. |
| `RUNTIME_ENV` | `prd`; Compose/host development set `dev`. |
| `JWT_VERIFICATION_KEY` / `JWT_JWKS_FILE` | Production JWT verification; choose one. |
| `AGENTOS_URL` | Scheduler/OAuth origin; default `http://127.0.0.1:8000`. |
| `MCP_CONNECT_SECRET` | Optional OAuth connect secret, at least 16 characters. Agno generates the signing key and persists it in PostgreSQL across redeploys. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_DATABASE` | Defaults: `localhost`, `5432`, `ai`, `ai`, `ai`. |
| `DB_DRIVER` | `postgresql+psycopg`. |
| `PARALLEL_API_KEY` | Optional authenticated web access; otherwise keyless MCP. |
| `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` | Both enable the Slack interface. |
| `PORT`, `AGNO_DEBUG`, `WAIT_FOR_DB` | Railway service port (`8000`, matching its start command), debug output, container database wait. |
| `SANDBOX_ENABLED` | `false`; enable Docker engineering in development. |
| `SANDBOX_IMAGE` | `agno-sandbox:local` for dev; pushed ECR URI for runtime provisioning. |
| `SANDBOX_RUNTIME_ARN` | Runs engineers in production AgentCore instead of on the AgentOS server. |
| `ANTHROPIC_API_KEY`, `GITHUB_READ_TOKEN` | Local Claude and optional private repository read access. |
| `AWS_REGION` | Claude/Bedrock region inside the sandbox; defaults to `us-east-1`. The host AgentCore client uses the runtime ARN’s region. |
| `AWS_PROFILE` | Optional host AWS credential profile; it must exist on the API host. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | Alternative host AWS credentials. |
| `MCP_CHECK_HOST`, `MCP_CHECK_TOKEN` | Run the probe on the host; optional existing bearer token. |
