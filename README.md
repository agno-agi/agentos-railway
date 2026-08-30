# AgentOS: The Agent Platform That Powers Your Product

AgentOS is a durable agent runtime that serves agents over REST, MCP, and chat interfaces like Slack. Build customer-facing agents and serve them to your users from your product, through AI apps like Claude and ChatGPT, or interfaces like Slack.

AgentOS gives you one agent backend for every frontend.

**Three ways to build agents.**

1. **Coding agent.** Point a coding agent at the skills in [`.agents/skills/`](.agents/skills/) and it can create, improve and evaluate your agents for you.
2. **Natural language.** Ask the built-in Platform Builder to build agents for you.
3. **No-code Studio.** Build agents visually using the [AgentOS Studio](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-railway).

**Three ways to serve your agents to your users.**

1. **Your product.** Call the AgentOS REST API from your product.
2. **AI apps.** Connect your agents to Claude and ChatGPT using the AgentOS MCP server.
3. **Chat interfaces.** Distribute your agents through Slack, WhatsApp (and more) using AgentOS Interfaces.

**Monitor and govern your agents.**

The [AgentOS Control Plane](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-railway) gives you a unified view of your agent platform. Trace every action. Enforce agent- and tool-level permissions.

<img width="3298" height="2412" alt="AgentOS" src="https://github.com/user-attachments/assets/40a53a42-d4d2-402b-8e92-742609207957" />

<p align="center"><em>Everything runs in your cloud, your data lives in your database.</em></p>

## Get Started

Copy this prompt into your favorite coding agent. It sets up the platform and builds your first agent for you:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform, cd in, and run the setup-platform skill (in .agents/skills/).
```

Your coding agent checks Docker, sets up `.env`, boots the platform, verifies the MCP endpoint, connects to the AgentOS UI, then builds your first agent. Prefer to drive yourself? See [Manual Setup](#manual-setup).

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

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-railway) and sign in.
2. Click **Connect OS**, enter `http://localhost:8000` as the URL, name it **Local AgentOS**, and connect.

### Step 3: Build your first agent using natural language

1. Click **Chat** under the **Agno** team and tell it what you're working on: "Help me build an agent for my product".
2. Give it the docs URL for your product, or for a product you like — `docs.agno.com`, say.
3. Click the **Refresh** button on the top right. You should now see your new agent in the **Agents** dropdown. Chat with it directly, or just ask Agno to run it for you.

## Make the platform yours

Your cloned repo points at this public template. Create your own GitHub repo and point your platform at it:

```sh
git remote rename origin upstream    # keep the template connected for updates
git remote add origin <your-private-repo-url>
git push -u origin main
```

> **Heads up.** Create the private repo first ([github.com/new](https://github.com/new), or `gh repo create <name> --private`). Keep `upstream` connected, so that `git pull upstream main` brings in template updates in the future.

## Run in production

You can run the platform anywhere that supports containers. This codebase comes with scripts to deploy the platform to [Railway](https://railway.com) — and a coding-agent skill, [`/deploy-platform`](.agents/skills/deploy-platform/SKILL.md), that will help you deploy it.

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

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-railway), click **Connect OS** → **Live**, and enter your Railway domain.
2. Name it **Live AgentOS**, flip **Token-Based Authorization (JWT)** on and connect. The UI generates your public key. (Ran into an issue? Go to **Settings** → **OS & Security** → **Token-Based Authorization (JWT)** to get the key from the settings page.)
3. Copy the public key.
4. Paste the full public key into the `up.sh` prompt. The script saves it into your env file for future syncs:

```sh
JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
```

If you get something wrong, you can re-sync environment variables with `./scripts/railway/env-sync.sh`.

### 4. Verify

You can check the logs on the Railway dashboard, or by running the following command:

```sh
railway logs --service agent-os
```

### 5. Connect your AgentOS to MCP clients

AgentOS comes with an MCP server at `/mcp` (enabled by setting `mcp=True` in [`app/main.py`](app/main.py)). There are two ways to connect your AgentOS to MCP clients:

1. **AI Apps like Claude and ChatGPT** connect to your AgentOS over the internet using OAuth. Add `https://<railway-domain>/mcp` as a custom connector in the chat app's connector settings. Leave the form's optional OAuth fields (client ID / client secret) empty. Click **Connect** and, on the consent page, enter the `MCP_CONNECT_SECRET` that `up.sh` generated during deploy (saved in `.env.production`).
2. **Coding agents like Claude Code, Claude Desktop, Codex, and Cursor** connect to your AgentOS via the MCP URL. Register your AgentOS with the MCP clients on your machine:

```sh
uvx agno connect --url https://<railway-domain>
```

After a successful connection, open one of these apps and ask:

```text
can you access my agentos mcp?
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

Deletes the Railway project: the agent-os service, the pgvector database, and its volume, **including all data**. It also comments out the Railway-minted `AGENTOS_URL` and `JWT_VERIFICATION_KEY` in your env file, so a future `up.sh` derives a fresh domain and re-runs its guided key step. Custom domains are preserved.

### Opting out of JWT (not recommended)

Change `authorization=runtime_env != "dev"` to `authorization=False` in [`app/main.py`](app/main.py) and redeploy. Use this only inside a private VPC behind another auth layer. Without it, anyone who guesses your Railway domain can access your platform.

## Using the platform

This platform is designed so that coding agents can drive the entire **create → improve → evaluate → maintain** lifecycle for you.

### Create

Open your coding agent of choice (Claude Code, Codex, Cursor) and run:

```
/create-agent
```

It asks a few questions, generates the agent file in `agents/`, registers it in `app/main.py`, adds its description and quick prompts to `app/config.yaml`, restarts the container, and smoke-tests it for you.

### Improve

Improve your agents by running the following skills:

- **`/extend-agent`** — Add a tool, add a capability, refine the instructions, fix a known bug.
- **`/improve-agent`** — Claude simulates scenarios from the agent's `INSTRUCTIONS` and its real usage recorded in the database, runs them against the live container, judges the responses, and edits until they pass.

### Evaluate

Run the eval suite to check for regressions. The evals live in [`evals/cases.py`](evals/cases.py), and run history shows up in the AgentOS UI next to your sessions and traces.

The evals run on the host machine, so set up the venv with `./scripts/venv_setup.sh && source .venv/bin/activate`, then run:

```sh
python -m evals --tag smoke      # fast checks of the self-driving surfaces
python -m evals --tag release    # broader pre-release confidence
python -m evals --name <case>    # one case while iterating
python -m evals -v               # stream the full run with rich panels
```

If a case fails, run **`/eval-and-improve`** — it diagnoses each failure, fixes what's in scope, and loops until green.

### Maintain

Because the repo is managed by coding agents, it moves fast. Run `/review-and-improve` before a release or after a refactor: it sweeps for drift between docs, code, and config, auto-fixes mechanical drift like stale paths and missing env vars, and flags anything bigger.

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
| `EVALS_SUITE_TIMEOUT_SECONDS` | no | derived | Whole-suite timeout for run-evals runs; per-case timeouts are the granular limit. Unset, it is derived from the cases the tag selects. Set it to override. |
| `PARALLEL_API_KEY` | no | none | Authenticates Agno's and the Studio registry's web search tools (Parallel SDK when set; keyless MCP fallback). Also the fast route for ingesting a product's docs — clean markdown per page, JS-rendered pages and PDFs included; without it ingestion still works, page by page, just slower. |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | no | none | Both must be set to enable the Slack interface. The bot token also lights up the registry's send-only Slack toolkit for built agents. |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | no | matches compose | Postgres connection. |
| `DB_DRIVER` | no | `postgresql+psycopg` | SQLAlchemy driver. |
| `AGNO_DEBUG` | no | `False` | If `True`, Agno emits verbose debug logs. Compose sets this for dev. |
| `WAIT_FOR_DB` | no | `False` | If `True`, the entrypoint blocks on the DB before starting. Compose sets this. |

## Learn more

- [Agno documentation](https://docs.agno.com?utm_source=github&utm_medium=template&utm_campaign=agentos-railway)
- [AgentOS introduction](https://docs.agno.com/agent-os/introduction?utm_source=github&utm_medium=template&utm_campaign=agentos-railway)
- [Agno on GitHub](https://github.com/agno-agi/agno). Drop a star if this is useful.
