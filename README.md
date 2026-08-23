# AgentOS: The Agent Platform That Builds Itself

AgentOS turns your agents into a production API and MCP server. One AI backend that serves every frontend — and a platform that grows itself: coding agents build it at the source, and the platform builds new agents, teams, and workflows at runtime.

1. **Your product.** Call the REST API from your app: run agents, stream responses, and manage sessions, memory, and knowledge.
2. **AgentOS UI.** Chat with agents, build new ones, inspect sessions, traces, memory, and evals from the AgentOS UI at [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-railway&utm_content=agentos-railway&utm_term=railway).
3. **Coding agents.** Manage the full agent development lifecycle (create, extend, improve, eval, review) using the skills in [`.agents/skills/`](.agents/skills/).
4. **AI apps.** Use your agents from Claude and ChatGPT using the MCP server at `/mcp`.
5. **Chat interfaces.** Chat with your agents from Slack — set two env vars and it's live. WhatsApp, Telegram, and Discord follow the same conditional pattern with agno's other interfaces.

<img width="3298" height="2412" alt="AgentOS" src="https://github.com/user-attachments/assets/40a53a42-d4d2-402b-8e92-742609207957" />

<p align="center"><em>Built on the <a href="https://docs.agno.com">Agno framework</a>. Everything runs in your cloud, your data lives in your database.</em></p>

## Get Started

Copy this prompt into your favorite coding agent. It sets up the platform and builds your first agent with you:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform, cd in, and run the setup-platform skill (in .agents/skills/).
```

Your coding agent drives the whole flow: it checks Docker, sets up `.env`, boots the platform, verifies the MCP endpoint, connects the AgentOS UI, and builds your first agent with you. Prefer to drive yourself? See [Manual Setup](#manual-setup).

## Built for agents

This codebase comes with:

- **Agno — the platform, speaking for itself.** "Agno, we're going with PlanetScale over RDS." "Agno, build me an agent that tracks AI news." Tell it anything — decisions, who's on what, what you learned — and it files the who and the why, learns how you work, and connects the dots when someone asks what's happening. Agno holds the thread; everything else is a handoff: it leads the three platform agents and runs everything your team builds, so building things, checking on the platform, and understanding it all work through the same name — from Slack too. Notes and entities are shared by everyone on the platform, so what the team files is there whichever frontend you ask from. What Agno learns about *you* follows your identity, which a deployment with JWT gives you across every channel.
- **Three platform agents** behind it, one per job. **Platform Builder** creates agents, teams, workflows, and schedules using the AgentOS Studio — builds come out published and runnable. **Platform Manager** monitors what the platform is doing: usage, run activity, eval history, deployment checks, schedules. **Platform Engineer** knows how the platform is built: it reads the source and explains the wiring, grounded in real files.
- **A safe registry, so "builds itself" is bounded.** [`app/registry.py`](app/registry.py) declares exactly what a component built at runtime may be given: web search, the shared notebook, media and file generation, a knowledge base, the platform's per-user memory, a step-function library. Platform Builder composes from that list and cannot extend it — new capability is a reviewed code change, which is why letting agents build agents is safe to leave on.
- **Coding-agent skills** let Claude Code, Codex, Cursor, and other coding agents build, test, and improve the platform at the source — including growing that registry — see [Using the platform](#using-the-platform).

Trace data, agent code, evals, and system logs are all available to coding agents, so the platform can inspect and improve itself end to end.

## Manual Setup

### Step 1: Run locally

> **Prerequisite:** [Docker](https://www.docker.com/get-started/) installed and running.

```sh
git clone https://github.com/agno-agi/agentos-railway agentos
cd agentos

# Configure credentials
cp example.env .env
# Open .env and set OPENAI_API_KEY

# Run the platform on docker
docker compose up -d --build
```

Confirm your AgentOS is running at [http://localhost:8000/docs](http://localhost:8000/docs).

### Step 2: Connect the AgentOS UI

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-railway&utm_content=agentos-railway&utm_term=railway) and sign in.
2. Click **Connect OS**, enter `http://localhost:8000` as the URL, name it **Local AgentOS**, and connect.

### Step 3: Meet Agno — and build your first agent through it

1. Click **Chat** under the **Agno** team and tell it what you're working on: "Hey Agno — I'm building a support bot." It files the who and what as entities, the why as notes, and what it learns about you stays yours.
2. Now ask it to build: "Build an agent that tracks AI news and writes a daily brief". Agno hands the build to Platform Builder, and the agent comes back created **and published** — live on the platform.
3. Click the **Refresh** button on the top right. You should now see the "Daily AI News Brief" agent in the **Agents** dropdown — chat with it directly, or just tell Agno: "Have the news agent brief me."

From then on, tag Agno in from anywhere — this UI, Slack, claude.ai, ChatGPT — and ask "Agno, what's happening?": same Agno everywhere.

### Step 4: Check platform health

Click **Chat** under **Platform Manager** and ask: "How healthy is the platform?" It answers from runtime data — eval history, deployment checks, schedules, and the run activity of the agent you just built.

### Step 5: See how it's built

Click **Chat** under **Platform Engineer** and ask: "Tell me about this AgentOS." It reads the repo and gives you the tour — the agents, the skills, the wiring — grounded in real files. Any time you wonder how something works, this is the agent that knows.

### Step 6: Make it yours

Your clone's `origin` points at this public template — a repo you can't push to. Give your platform a home of its own:

```sh
git remote rename origin upstream    # keep the template connected for updates
git remote add origin <your-private-repo-url>
git push -u origin main
```

Create the private repo first ([github.com/new](https://github.com/new), or `gh repo create <name> --private`). `upstream` stays connected, so `git pull upstream main` brings in template updates whenever you want them.

## Run in production

You can run the platform anywhere that supports containerized images. This codebase comes with scripts to deploy the platform to [Railway](https://railway.com) — and a coding-agent skill, [`/deploy-platform`](.agents/skills/deploy-platform/SKILL.md), that drives them for you and verifies the live platform at the end.

> **Prerequisite:** [Railway CLI](https://docs.railway.com/cli#installing-the-cli) installed and `railway login` completed.

### 1. Set up your production env

Create a new `.env.production` file for production credentials.

```sh
cp .env .env.production          # or cp example.env .env.production
# Edit .env.production with production values
```

Keeping a separate `.env.production` lets us use different values for local and production: different OpenAI keys, production-only credentials, a different Slack workspace.

### 2. Deploy

```sh
./scripts/railway/up.sh
```

This provisions the AgentOS service and Postgres on the same private network. The script pauses and asks for a JWT verification key for authentication (see next section).

### 3. Production Auth

Token-Based Authorization is on by default. Without a `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE`, the app refuses to serve traffic in production. The platform's job is to keep your data private, so the safe default is "refuse to start" without an authentication token.

Token-Based Auth gives you three things:

1. **No public access.** The server rejects requests without a valid token.
2. **Per-request identity.** Middleware parses the token and extracts the `user_id`, `session_id`, and custom claims. Each request is tied to a user and session, giving you auditability and traceability.
3. **Granular permissions.** Scopes on the token decide what each caller can do — run agents, read sessions, manage the platform. Admin tokens can do everything; scoped tokens get exactly what their claims grant.

During `./scripts/railway/up.sh`, the script creates your Railway domain and pauses so you can mint the key before the app starts.

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-railway&utm_content=agentos-railway&utm_term=railway), click **Connect OS** → **Live**, and enter your Railway domain.
2. Name it **Live AgentOS**, flip **Token-Based Authorization (JWT)** on — the toggle is right on the connect panel — and connect. The UI generates your public key. (Already connected without it? **Settings** → **OS & Security** → **Token-Based Authorization (JWT)**.)
3. Copy the public key.
4. Paste the full public key into the `up.sh` prompt. The script saves it into your env file for future syncs:

```sh
JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
```

> **Heads up.** Live AgentOS Connections are a paid feature. Use `PLATFORM30` to get 1 month off. We are working on a free trial so you don't have to pay to try.

If you get something wrong, you can re-sync environment variables with `./scripts/railway/env-sync.sh`.

### 4. Register your production AgentOS to MCP clients

Re-run `uvx agno connect`, this time pointed at your deployed domain, to connect Claude Code, Claude Desktop, Codex, and Cursor to your production platform:

```sh
uvx agno connect --url https://<railway-domain>
```

For **claude.ai and ChatGPT (web)**: add `https://<railway-domain>/mcp` as a custom connector in the chat app's connector settings. Leave the form's optional OAuth fields (client ID / client secret) empty. Click **Connect** and, on the consent page, enter the `MCP_CONNECT_SECRET` that `up.sh` generated during deploy (saved in `.env.production`).

### 5. Verify

You can check the logs on the Railway dashboard, or by running the following command:

```sh
railway logs --service agent-os
```

### Redeploy after code changes

To redeploy your AgentOS, run the following command:

```sh
./scripts/railway/redeploy.sh
```

Recommended: Auto-deploy on merge to `main` using:

1. Open the Railway dashboard, your project, the agent-os service, **Settings**.
2. Under **Source**, click **Connect Repo** and pick your repo.
3. Set the deploy branch to `main` and save.

Push to `main` triggers a build and rolling deploy. `./scripts/railway/env-sync.sh` is still how you sync env changes.

### Sync environment variables

To re-sync environment variables, run the following command:

```sh
./scripts/railway/env-sync.sh
```

### Tear down

```sh
./scripts/railway/down.sh
```

Deletes the Railway project: the agent-os service, the pgvector database, and its volume, **including all data**. It also comments out a Railway-generated `AGENTOS_URL` in your env file so a future `up.sh` derives it again. Custom domains are preserved.

### Opting out of JWT (not recommended)

Change `authorization=runtime_env != "dev"` to `authorization=False` in [`app/main.py`](app/main.py) and redeploy. Use this only inside a private VPC behind another auth layer. Without it, anyone who guesses your Railway domain can access your platform.

## Using the platform

This platform is designed so that coding agents can drive the entire **create → improve → evaluate → maintain** lifecycle for you.

### Create

Open your coding agent of choice (Claude Code, Codex, Cursor) and run:

```
/create-agent
```

It asks a few questions, generates the agent file in `agents/`, registers it in `app/main.py`, adds its description and quick prompts to `app/config.yaml`, restarts the container, and smoke-tests it live.

### Improve

Improve your agents by running the following skills:

- **`/extend-agent`** — Add a tool, add a capability, refine the instructions, fix a known bug.
- **`/improve-agent`** — Claude simulates scenarios from the agent's `INSTRUCTIONS` and its real usage recorded in the database, runs them against the live container, judges the responses, and edits until they pass.

### Evaluate

Run the eval suite to check for regressions. The evals live in [`evals/cases.py`](evals/cases.py), and run history shows up at os.agno.com next to your sessions and traces.

The evals run on the host machine, so set up the venv with `./scripts/venv_setup.sh && source .venv/bin/activate`, then:

```sh
python -m evals --tag smoke      # fast checks of the self-driving surfaces
python -m evals --tag release    # broader pre-release confidence
python -m evals --name <case>    # one case while iterating
python -m evals -v               # stream the full run with rich panels
```

If a case fails, run **`/eval-and-improve`** — it diagnoses each failure, fixes what's in scope, and loops until green. And when you build an agent of your own, **`/create-evals`** writes its coverage: it mines your real sessions for scenarios and adds cases the scheduled eval run watches from then on.

### Maintain

Because the repo is managed by coding agents, it moves fast. Run `/review-and-improve` before a release or after a refactor: it sweeps for drift between docs, code, and config, auto-fixes mechanical drift like stale paths and missing env vars, and flags anything bigger.

## Connect more frontends (optional)

AgentOS comes with an MCP server at `/mcp` (enabled by setting `mcp_server=True` in [`app/main.py`](app/main.py)), so any MCP client can call your agents, teams, and workflows through tools like `run_agent`, `run_team`, and `run_workflow`.

Register your AgentOS with the MCP clients on your machine:

```sh
uvx agno connect
```

It auto-detects Claude Code, Claude Desktop, Codex, and Cursor and registers `http://localhost:8000/mcp`. After a successful connection, open one of these apps and ask:

```text
can you access my agentos mcp?
```

**claude.ai and ChatGPT (web).** Hosted AI apps reach your platform over the internet and need an OAuth login. Deploy to production (above), add `https://<domain>/mcp` as a remote connector, and approve the consent page with your connect secret.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | yes | none | OpenAI key for models and embeddings. |
| `RUNTIME_ENV` | no | `prd` | `dev` disables JWT. Compose sets this to `dev` for local — never put it in an env file that syncs to Railway, or production deploys unauthenticated. |
| `JWT_VERIFICATION_KEY` | prd | none | Public key from os.agno.com. Required when `RUNTIME_ENV=prd`, unless `JWT_JWKS_FILE` is set. |
| `JWT_JWKS_FILE` | prd | none | Path to a JWKS file; alternative to `JWT_VERIFICATION_KEY` for production JWT verification. |
| `AGENTOS_URL` | no | `http://127.0.0.1:8000` | Scheduler base URL. `scripts/railway/up.sh` auto-sets it to your Railway domain; set by hand only for a custom domain or tunnel. Also the public origin OAuth metadata derives from when `MCP_CONNECT_SECRET` is set. |
| `MCP_CONNECT_SECRET` | no | none | If set (≥16 chars, e.g. `openssl rand -base64 32`), `/mcp` becomes its own OAuth 2.1 authorization server so claude.ai and ChatGPT (web) can connect; connecting asks for this secret on a consent page. Requires `AGENTOS_URL`. `scripts/railway/up.sh` auto-generates it on deploy. PAT and JWT bearers keep working alongside. |
| `AGENTOS_MCP_SIGNING_KEY` | no | none | Optional high-entropy signing-key material (≥32 chars) for OAuth tokens. Unset, a strong key is generated and persisted in the database. Rotating it invalidates outstanding tokens. |
| `ENABLE_DEPLOY_CHECK` | no | `True` | The reference deployment-check cron runs daily by default. This env var owns the schedule's toggle (re-asserted on every boot); the workflow is runnable on demand regardless. |
| `EVALS_TAG` | no | `smoke` | Eval tag run by the run-evals workflow. |
| `EVALS_CASE_TIMEOUT_SECONDS` | no | `90` | Default per-case timeout for run-evals runs; applies only to cases that don't set their own `timeout_seconds`. |
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | `900` | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. The default bounds the `smoke` tag's worst case (incl. builder-case teardown). |
| `PARALLEL_API_KEY` | no | none | Authenticates Agno's and the Studio registry's web search tools (Parallel SDK when set; keyless MCP fallback). |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | no | none | Both must be set to enable the Slack interface. The bot token also lights up the registry's send-only Slack toolkit for built agents. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, Agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Learn more

- [Agno documentation](https://docs.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-railway&utm_content=agentos-railway&utm_term=railway)
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction?utm_source=github&utm_medium=example-repo&utm_campaign=agentos-railway&utm_content=agentos-railway&utm_term=railway)
- [Agno on GitHub](https://github.com/agno-agi/agno). Drop a star if this is useful.
