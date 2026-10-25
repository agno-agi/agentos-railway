# AgentOS: The Agent Platform That Builds Itself

AgentOS is a durable agent runtime that serves agents over API, MCP, and chat interfaces like Slack.
Build agents for your product, your team, or yourself. Run them in your own cloud,
keep their data in your own database, and manage them from [AgentOS](https://os.agno.com).

Built with [Agno](https://github.com/agno-agi/agno), this template gives you a working
agent platform that you can run locally or deploy to Railway.

**Three ways to build agents.**

1. **Use a coding agent.** Open the repo in Claude Code, Codex, or Cursor. The included
   skills help it create, test, and improve your agents.
2. **Describe what you need.** Chat with OS Manager, the built-in agent that helps you
   manage the platform and build new agents.
3. **Use Studio.** Build agents visually in [AgentOS Studio](https://os.agno.com).

**Three ways to use your agents.**

1. **In your product.** Call your agents through the REST API.
2. **In AI apps.** Connect apps such as Claude and ChatGPT through MCP.
3. **In Slack.** Connect a Slack app to talk to OS Manager from your workspace.

The AgentOS UI lets you chat with your agents, review past conversations, and see
the steps an agent took. Your PostgreSQL database stores conversations, memories,
and Company work.

## Get started

Copy this prompt into your coding agent:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

It checks Docker, helps you add your API key, starts the platform, and walks you
through building your first agent. Already cloned the repo? Ask your coding agent
to follow [setup-platform](.agents/skills/setup-platform/SKILL.md) in that folder.

Prefer to set it up yourself? Follow the steps below.

## Engineers

The platform includes **Claude Engineer** and **Codex Engineer**. They can read your
code, make changes, and run commands.

Chat with either engineer in AgentOS, or ask OS Manager to use one:

> Ask Codex Engineer to review this project and suggest improvements. Don't change any files yet.

Codex uses the `OPENAI_API_KEY` you added during setup. To use Claude, add
`ANTHROPIC_API_KEY` to `.env`. After changing `.env`, run `docker compose up -d` again.

By default, engineers work in this project's folder. With Docker Compose, they
can change files in your local checkout, including the code serving the platform.
Review those changes before committing them.

For engineers to work in a separate environment, configure a sandbox with your
own repository URL and branch:

- [Local Docker sandbox](docs/sandboxes.md#local-docker-sandbox): run the API on
  your computer and engineering work in a separate Docker container.
- [AWS AgentCore sandbox](docs/sandboxes.md#aws-agentcore-sandbox): run engineering
  work remotely when the platform is deployed. The API host needs AWS credentials
  and persistent checkpoint storage at `/data`.

Both engineers stay available with either setup. Sandboxes are optional and are
not enabled by the default Compose configuration.

## Run locally

You'll need Git, Docker with Compose, and an OpenAI API key. Make sure Docker is running.
Run the commands below in a terminal.

### 1. Start the platform

```sh
git clone https://github.com/agno-agi/agentos-railway agent-platform
cd agent-platform
cp example.env .env
```

Open `.env` and set `OPENAI_API_KEY`. Then start the platform:

```sh
docker compose up -d --build
```

The first build can take a few minutes. When it's ready, open
[http://localhost:8000/docs](http://localhost:8000/docs) to see the API.

Check that AI apps can connect through MCP:

```sh
./scripts/mcp_check.sh
```

The check should report `9 tools; required tools available`.

### 2. Connect the UI

1. Open [os.agno.com](https://os.agno.com) and sign in.
2. Choose **Connect OS**, select a local connection, and enter `http://localhost:8000`.
3. Name it **Local AgentOS**, then open the chat for **OS Manager**.

### 3. Build your first agent

Tell OS Manager what you want to build. For example:

> Help me build an agent that answers questions about my product. Here's the documentation URL: …

Review what it proposes, then ask it to build and publish the agent.
Refresh the Agents list and try it out. You can chat with your new agent directly
or ask OS Manager to run it for you.

## Build and improve your agents

You can keep working through OS Manager, use Studio, or edit Python files in this repo.
The repo includes instructions, called skills, for common coding tasks.
Ask your coding agent to follow the relevant skill:

| What you want to do | Skill |
| --- | --- |
| Build an agent | [/create-agent](.agents/skills/create-agent/SKILL.md) |
| Add a tool, change behavior, or fix a bug | [/extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Write tests for your agent's answers | [/create-evals](.agents/skills/create-evals/SKILL.md) |
| Fix failing tests or try more scenarios | [/eval-and-improve](.agents/skills/eval-and-improve/SKILL.md) |
| Check the repo before sharing or releasing it | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

If you write an agent in Python, put it in `agents/` and add it to
[app/main.py](app/main.py) so the platform can run it. Set its description and
suggested prompts in [app/config.yaml](app/config.yaml). To make a tool or model
available in Studio, add it to [app/registry.py](app/registry.py).

You can give agents documents to search, a notebook to keep notes, and memory
to remember each user. Keep a product's documentation in its own knowledge base,
separate from the platform's documents.

## Company

Company organizes ongoing work. A **Product** is what you're working on, a
**Project** groups related work, and a **Task** is one piece of work to complete.
A **Routine** is a set of instructions that can run on a schedule.

This template includes an **AgentOS** Product for improving the platform itself.
To get started, ask OS Manager:

> Review this codebase and recent Agno releases. Suggest the most useful improvements.

It also includes a daily review at **09:00 UTC**. Company Manager reads the code
and Agno release notes, then proposes up to three Tasks for you to review.
The review is instructed to suggest work and leave approval and execution to you.
Automatic acceptance is off.

Scheduled reviews use your model API keys and incur usage costs. Check the saved
schedule and run history in Company to see when a review will run and what it did.

[app/company.py](app/company.py) sets the initial review instructions and schedule.
Once they're saved in the database, update the saved Routine to change them;
editing the Python file alone won't change an existing Routine.

## Make it yours

To save your work in your own GitHub repository, create an empty private repo.
From a fresh clone of this template, run the commands below with your repo URL.
This makes `origin` your repo and keeps the original template as `upstream`:

```sh
git remote rename origin upstream
git remote add origin https://github.com/YOUR-ORG/YOUR-REPO.git
git push -u origin HEAD
```

Future pushes go to your repository. You can still fetch updates from `upstream`
and review them before merging.

If you use sandboxes, also set the repository URL and branch in
[the sandbox configuration](docs/sandboxes.md#choose-your-repository).

<a id="deploy-in-production"></a>

## Deploy on Railway

Ask your coding agent to follow [deploy-platform](.agents/skills/deploy-platform/SKILL.md),
or follow the steps below yourself.

Already deployed? Use the [update commands](#update-or-remove-the-deployment).
Upgrading from an older template? Read the [upgrade guide](docs/upgrading.md) first.

### 1. Prepare your production settings

Install [uv](https://docs.astral.sh/uv/) and Railway CLI **5.49.0 or newer**, then run
`railway login`. Set up the Python environment used by the deploy scripts
(run `deactivate` first if another environment is active):

```sh
./scripts/venv_setup.sh
[ -f .env.production ] || cp example.env .env.production
```

Open `.env.production` and add `OPENAI_API_KEY`, plus any other API keys you use.
This file holds your Railway settings; `.env` holds your local settings.
Keep `RUNTIME_ENV=prd`, or leave it unset.

### 2. Create the Railway project

Replace `YOUR_WORKSPACE` with your Railway workspace name or ID:

```sh
./scripts/railway/up.sh --workspace YOUR_WORKSPACE
```

This creates the API service, PostgreSQL database, and public URL. Railway starts
billing for these resources. The script saves the URL and connection settings in
`.env.production`.

On a first deployment without authentication settings, the script creates the
resources and URL, then stops before starting the API. This is expected
(exit code `2`). Continue with step 3 to finish setup; don't run `up.sh` again.

### 3. Set up authentication

1. Open [os.agno.com](https://os.agno.com), choose **Connect OS**, and select **Live**.
2. Enter the URL saved as `AGENTOS_URL` in `.env.production` and enable token-based authorization.
3. Copy the public verification key into `.env.production` as `JWT_VERIFICATION_KEY`.
   Wrap the full key in quotes, including its first and last lines.
4. Upload the settings and deploy:

```sh
./scripts/railway/env-sync.sh --no-deploy
./scripts/railway/redeploy.sh
```

Your deployed agents and data require a valid login token. The verification key
lets the server check those tokens.

Check the deployment logs:

```sh
railway logs --service agent-os
```

Confirm that `/health` responds and that you can connect through the UI. Before sharing,
check that a request to `/agents` without a token is rejected and one with a valid token works.

### 4. Connect your AI apps

To connect an AI app that supports MCP, use your Railway URL followed by `/mcp`
(for example, `https://YOUR-DOMAIN/mcp`). When the connection page asks for a
secret, enter the `MCP_CONNECT_SECRET` saved in `.env.production`.

To connect a supported coding client from your terminal, use your Railway URL:

```sh
uvx agno connect --url https://YOUR-DOMAIN
```

Once connected, the app can talk to OS Manager through the `agno` tool.
Try asking it about your platform to check the connection. Opening `/mcp`
in a browser is not enough to check that an agent can respond.

### Sandbox storage

If you use AWS AgentCore for engineers, the API needs a persistent `/data` volume.
For a new Railway deployment, add `--with-checkpoint-volume` to `up.sh`:

```sh
./scripts/railway/up.sh --workspace YOUR_WORKSPACE --with-checkpoint-volume
```

For an existing deployment, add the volume before enabling AgentCore:

```sh
railway volume --service agent-os add --mount-path /data
```

### Update or remove the deployment

| What you want to do | Command |
| --- | --- |
| Deploy code changes | `./scripts/railway/redeploy.sh` |
| Upload settings and redeploy | `./scripts/railway/env-sync.sh` |
| Deploy code and settings together | Run `./scripts/railway/env-sync.sh --no-deploy`, then `./scripts/railway/redeploy.sh` |
| View logs | `railway logs --service agent-os` |
| Delete the project | `./scripts/railway/down.sh` |

**Deleting the project deletes its database and all its data.** Local env files are
kept; review their saved URL and authentication settings before creating a new project.

Removing a line from `.env.production` does not remove it from Railway. Clear an
optional credential by setting it to an empty value, or remove it in Railway.
Changing the database password needs a separate database update.

## Verify and develop

To check your Python code and test agent responses, install [uv](https://docs.astral.sh/uv/)
and run these commands from the project folder. Keep the local platform running.
If another Python environment is active, run `deactivate` first.

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
./scripts/validate.sh
python -m evals --tag smoke
```

`validate.sh` checks Python formatting, lint rules, and types. The smoke tests ask
OS Manager to explain setup, check platform health, and explain agent memory.
They use your model API keys and save results in the database for review in the UI.
PostgreSQL must be running, even when you only want to list the tests.

Add your own cases in [evals/cases.py](evals/cases.py), or use
[/create-evals](.agents/skills/create-evals/SKILL.md). To save a report, add
`--json-output tmp/evals.json`. To run one case, use `--name CASE_NAME`.
Evals use your application's database and workspace; agents can call tools during a test.

Change dependencies in `pyproject.toml`, then run `./scripts/generate_requirements.sh`.
Commit the updated `requirements.txt` and rebuild the API and any sandbox image you use.
See [AGENTS.md](AGENTS.md) for the code layout and development conventions.

## Configuration

[example.env](example.env) shows the main settings. Start with `OPENAI_API_KEY`;
add the others when you need them. Use `.env` locally and `.env.production` for Railway.

| Setting | What it's for |
| --- | --- |
| `OPENAI_API_KEY` | OS Manager, embeddings, and Codex Engineer. |
| `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` | Claude Engineer. |
| `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` | Connect OS Manager to Slack. Set both. |
| `PARALLEL_API_KEY` | Optional web search key. Without it, search uses Parallel's MCP server without an API key. |
| `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE` | Check login tokens in production. A JWKS file must be available on the server. |
| `AGENTOS_URL` | Public URL used by scheduled jobs and MCP. Railway setup saves it for you. |
| `MCP_CONNECT_SECRET` | Connect browser MCP clients. Railway setup generates it for you. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_DATABASE` | PostgreSQL connection settings. Local Compose configures these for you. |
| `RUNTIME_ENV` | `prd` by default. Local Compose uses `dev`, which disables token checks. |

## Learn more

- [Agno documentation](https://docs.agno.com)
- [Agno on GitHub](https://github.com/agno-agi/agno)
- [AgentOS UI](https://os.agno.com)
