# AgentOS: The self-managing agent platform

AgentOS is an open-source agent platform that runs in your cloud. It comes with a **Super Agent** that builds agents, coordinates their work, and helps you manage the platform. Ask it to run an agent, create a workflow, or break a larger goal into Projects and Tasks.

Built with [Agno](https://github.com/agno-agi/agno), AgentOS brings together:

- **Agents, teams, and workflows** you build in Python, Studio, or through Super Agent.
- **Memory, knowledge, and storage** backed by your own PostgreSQL database.
- **Permissions, human approvals, and scheduling** for managing work.
- **An API and MCP server** to use your agents in products, Claude, and ChatGPT.

Use the [AgentOS UI](https://os.agno.com) to chat with agents, inspect runs and traces,
and track their work. This template runs locally with Docker and deploys to Railway.

## Get started

Give this prompt to your coding agent:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

It checks Docker, helps you configure your API key, starts the platform, and builds
an agent with you. If you've already cloned the repo, ask it to run `/setup-platform`.

### Or run it yourself

You'll need Git, Docker, and an OpenAI API key.

```sh
git clone https://github.com/agno-agi/agentos-railway agent-platform
cd agent-platform
cp example.env .env
```

Set `OPENAI_API_KEY` in `.env`, then start the platform:

```sh
docker compose up -d --build
```

Once [localhost:8000/docs](http://localhost:8000/docs) loads:

1. Sign in at [os.agno.com](https://os.agno.com).
2. Choose **Connect OS**, select a local connection, and enter `http://localhost:8000`.
3. Open **Super Agent** and tell it what you're working on.

## Put Super Agent to work

Start with a concrete request:

> Build an agent that turns meeting notes into decisions and action items, then run it on these notes: …

Super Agent can use your existing agents or build one for the job. Agents it builds
appear in the Agents list and are available through the API and MCP.

For ongoing work, ask it to create a Project:

> Propose a Project to build a customer support agent. Break it into Tasks for my review.

The **Company** page keeps track of Products, Projects, Tasks, and scheduled Routines.
You can approve work, assign it, review results, and request changes there or through
Super Agent. Products describe ongoing responsibilities; Projects and Tasks organize
specific work; Routines run on a schedule.

This template includes a weekly maintenance Routine that reviews the platform for
relevant Agno updates, security issues, and quality problems. It is **disabled by
default**. Enable it from the Company page to receive proposals for review.

## Skills

This repo includes skills for building and managing your agent platform. Ask your
coding agent to follow the relevant skill:

| Task | Skill |
| --- | --- |
| Build an agent | [/create-agent](.agents/skills/create-agent/SKILL.md) |
| Add tools, change behavior, or fix a bug | [/extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Write evals | [/create-evals](.agents/skills/create-evals/SKILL.md) |
| Find weaknesses and improve reliability | [/improve](.agents/skills/improve/SKILL.md) |
| Review the repository before release | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

## Coding agents

This repo comes with **Claude Code** and **Codex** agents. Work with them directly in AgentOS or ask Super Agent to delegate work to them.

They're **off by default**. Follow the [harness setup guide](docs/harnesses.md) to
enable them and configure credentials and sandboxes.

Once enabled, ask Super Agent:

> Ask Codex Engineer to review this project and suggest improvements. Don't change any files yet.

Without a sandbox, engineers run on the API host with its file and credential access.
[Sandboxes](docs/harnesses.md#sandboxes-and-checkpoints) provide isolated execution
and checkpoint recovery.

## Make this platform yours

Create an empty private GitHub repository, then point this checkout at it:

```sh
git remote rename origin upstream
git remote add origin https://github.com/YOUR-ORG/YOUR-REPO.git
git push -u origin HEAD
```

Your work now goes to your repository; `upstream` keeps the template available for
updates. If you use sandboxes, also set your repository URL and branch in the
[harness configuration](docs/harnesses.md#sandboxes-and-checkpoints).

## Deploy in production

Ask your coding agent to follow
[/deploy-platform](.agents/skills/deploy-platform/SKILL.md). This template targets Railway.
You’ll need Railway CLI (`railway login`), Docker and OpenSSL.

Set `RAILWAY_PROJECT_NAME` if you need a specific project name. The scripts provision an API service and PostgreSQL, and link this checkout to the project.

Create `.env.production` from [example.env](example.env) if absent. Set `OPENAI_API_KEY`
and any other model credentials you need. Keep `RUNTIME_ENV=prd` or leave it unset.

```sh
./scripts/railway/up.sh
```

When setup provides the HTTPS URL, connect it as a **Live** connection at
[os.agno.com](https://os.agno.com). Enable JWT authorization in **Settings → OS Security**
and supply the public verification key. If the prompt was skipped, save the full quoted
multiline `JWT_VERIFICATION_KEY` in `.env.production`, then run
`./scripts/railway/env-sync.sh`. The API requires the key to start in production.

Railway reads project settings through its CLI; confirm the linked project before updates.
Use `./scripts/railway/redeploy.sh` for code and `./scripts/railway/env-sync.sh` for settings.

Keep `AGENTOS_URL` set to the public HTTPS URL for scheduling and MCP OAuth. Verify
`/health`, an authenticated UI connection, and rejection of anonymous `/agents` requests.
Run one API instance and read [scaling](docs/scaling.md) before adding replicas.
For optional hosted sandboxes, follow [harness setup](docs/harnesses.md) and preserve
`SANDBOX_PROVIDER=agentcore` plus the required AWS credentials, runtime and S3 settings.

## Connect to Claude, ChatGPT, and coding clients

For MCP clients like Claude and ChatGPT, set `MCP_CONNECT_SECRET` to a random secret in your production environment and apply it with the settings update command above. Connect the client to `https://YOUR-DOMAIN/mcp` and enter the secret on
the consent page.

For supported coding clients:

```sh
uvx agno connect --url https://YOUR-DOMAIN
```

## Local development

Install [uv](https://docs.astral.sh/uv/), then create and activate a virtual environment
from the repository root. If another environment is active, run `deactivate` first.

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
```

The setup script installs the application and development dependencies into `.venv`.
After making changes, format your code and check formatting, lint, and types:

```sh
./scripts/format.sh
./scripts/validate.sh
```

With PostgreSQL running, test Super Agent with the smoke evals. These spend model
calls and save results in the database:

```sh
python -m evals --tag smoke
```

Add cases in [evals/cases.py](evals/cases.py). Use `./scripts/mcp_check.sh` to check
the running MCP server without a model call.

See [AGENTS.md](AGENTS.md) for development conventions and
[Agno documentation](https://docs.agno.com) for framework guides.
