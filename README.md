# AgentOS: The Agent Platform That Builds Itself

AgentOS is a durable agent runtime that serves agents over API, MCP, and chat interfaces like Slack.
Build agents for your product, your team, or yourself. Run them in your own cloud,
keep their data in your own database, and manage them from [AgentOS](https://os.agno.com).

Built with [Agno](https://github.com/agno-agi/agno), this template gives you a working
agent platform that you can run locally or deploy to Railway.

**Three ways to build agents.**

1. **Use a coding agent.** Open the repo in Claude Code, Codex, or Cursor. The included
   skills help it create, test, and improve your agents.
2. **Describe what you need.** Ask the built-in OS Manager to build an agent for you.
3. **Use Studio.** Build agents visually in [AgentOS Studio](https://os.agno.com).

**Three ways to use your agents.**

1. **In your product.** Call your agents through the REST API.
2. **In AI apps.** Connect Claude, ChatGPT, and other MCP clients to your agents.
3. **In Slack.** Add your Slack credentials to talk to OS Manager from your workspace.

The AgentOS UI lets you chat with your agents, review past conversations, and trace
what happened during a run. PostgreSQL stores your conversations, agent memories, and work.

## Get started

Copy this prompt into your coding agent:

```text
Help me set up my agent platform and build my first agent.

Clone https://github.com/agno-agi/agentos-railway into a folder called agent-platform,
cd into it, and follow .agents/skills/setup-platform/SKILL.md.
```

It checks Docker, helps you add your API key, starts the platform, and walks you
through building your first agent. Already cloned the repo? Run
[/setup-platform](.agents/skills/setup-platform/SKILL.md).

Prefer to set it up yourself? Follow the steps below.

## Run locally

You'll need Git, Docker with Compose, and an OpenAI API key. Make sure Docker is running.

### 1. Start the platform

```sh
git clone https://github.com/agno-agi/agentos-railway agent-platform
cd agent-platform
[ -f .env ] || cp example.env .env
```

Open `.env` and set `OPENAI_API_KEY`. Then start the platform:

```sh
docker compose up -d --build
```

The first build can take a few minutes. When it's ready, open
[http://localhost:8000/docs](http://localhost:8000/docs) to see the API.
Check that the MCP server is working:

```sh
./scripts/mcp_check.sh
```

If the platform doesn't start, check `docker compose logs agentos-api agentos-db`.
Local development doesn't require login tokens. The API and database are only exposed
on your machine; [production requires authentication](#deploy-on-railway).

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
These skills help your coding agent handle the work:

| What you want to do | Skill |
| --- | --- |
| Build an agent | [/create-agent](.agents/skills/create-agent/SKILL.md) |
| Add a tool, change behavior, or fix a bug | [/extend-agent](.agents/skills/extend-agent/SKILL.md) |
| Write tests for your agent's answers | [/create-evals](.agents/skills/create-evals/SKILL.md) |
| Fix failing tests or try more scenarios | [/eval-and-improve](.agents/skills/eval-and-improve/SKILL.md) |
| Check the repo before sharing or releasing it | [/review-and-improve](.agents/skills/review-and-improve/SKILL.md) |

Put Python agents in `agents/` and register them in [app/main.py](app/main.py).
Add their descriptions and suggested prompts in [app/config.yaml](app/config.yaml).
The tools, models, and other building blocks available to Studio live in
[app/registry.py](app/registry.py).

The platform includes a knowledge base for your documents, a shared notebook, and
per-user memory that you can add to your agents. For an agent that answers questions
about a product, create a separate knowledge base for that product's documentation.

## Company

Company helps you organize work into Products, Projects, and Tasks. Ask OS Manager:

> Review this codebase and recent Agno releases. Suggest the most useful improvements.

This template includes an **AgentOS** Product for improving the platform itself.
Its daily review is scheduled for **09:00 UTC**. Company Manager reads the code and
Agno release notes, then proposes up to three improvements as Backlog Tasks.
It is instructed to leave approval and execution to you; automatic acceptance is off.
These reviews use model calls, so check the saved schedule and run history in your deployment.

Change the review instructions or schedule in [app/company.py](app/company.py).
That file sets the starting values for new records. For an existing deployment,
change the saved schedule too—editing the file does not overwrite it.

## Engineers

The platform includes **Claude Engineer** and **Codex Engineer**. They can read your
code, make changes, and run commands.

Chat with either engineer in AgentOS, or ask OS Manager to use one:

> Ask Codex Engineer to review this project and suggest improvements. Don't change any files yet.

Codex uses the `OPENAI_API_KEY` you added during setup. To use Claude, add
`ANTHROPIC_API_KEY` to `.env`. After changing `.env`, run `docker compose up -d` again.

By default, engineers work in this project's folder. When running locally with
Docker Compose, their file changes appear in your local checkout. Review those
changes before committing them.

You don't need to configure a sandbox or repository URL to get started.

To have engineers work on a separate copy of your repository, follow the
[sandbox setup guide](docs/sandboxes.md) for Docker or AWS AgentCore.

## Make it yours

Create an empty private GitHub repository for your platform. For a fresh clone,
keep this template as `upstream` and point `origin` at your new repo:

```sh
git remote rename origin upstream
git remote add origin https://github.com/YOUR-ORG/YOUR-REPO.git
git push -u origin HEAD
```

You can fetch future template updates from `upstream` and review them before merging.
Set `REPOSITORY` in [app/sandbox.py](app/sandbox.py) to your repo and branch when you
want to use sandboxes or add the repo as a Company source. Company keeps a local
source for reading this codebase and adds the remote Git source when configured.
For an existing deployment, check the Product's saved Sources and retire any old
template URL; changing the code does not remove saved Sources.

## Deploy on Railway

Run [/deploy-platform](.agents/skills/deploy-platform/SKILL.md) in your coding agent
for help with deployment. To do it yourself, follow these steps.

### 1. Prepare your production settings

Install [uv](https://docs.astral.sh/uv/) and Railway CLI **5.49.0 or newer**, then run
`railway login`. Set up the Python environment used by the deploy scripts
(run `deactivate` first if another environment is active):

```sh
./scripts/venv_setup.sh
[ -f .env.production ] || cp example.env .env.production
```

Open `.env.production` and set your production API keys. The deploy scripts read this
file, separately from your local `.env`. Keep `RUNTIME_ENV=prd`, or leave it unset.

### 2. Create the Railway project

Replace `YOUR_WORKSPACE` with your Railway workspace name or ID:

```sh
./scripts/railway/up.sh --workspace YOUR_WORKSPACE
```

This creates the API service, PostgreSQL database, and public URL. Railway starts
billing for these resources. The script saves the URL and connection settings in
`.env.production`.

If authentication isn't configured yet, the script stops with exit code `2` before
deploying the API. Complete the next step to finish. If the checkout is already linked
to a Railway project, use the update commands below instead of creating another one.

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

Production requires a valid token to access your agents and data. You can also use
`JWT_JWKS_FILE` instead of a public key, provided the file is available on the server.

Check the deployment logs:

```sh
railway logs --service agent-os
```

Confirm that `/health` responds and that you can connect through the UI. Before sharing,
check that a request to `/agents` without a token is rejected and one with a valid token works.

### 4. Connect your AI apps

For a browser MCP client, add `https://YOUR-DOMAIN/mcp` as a connector.
On the OAuth consent page, enter the `MCP_CONNECT_SECRET` saved in `.env.production`.

For coding clients, run:

```sh
uvx agno connect --url https://YOUR-DOMAIN
```

OS Manager is available as the `agno` MCP tool alongside the eight built-in tools.
Check MCP with an authenticated client before sharing the connection. Opening `/mcp`
in a browser only checks discovery; it doesn't test authentication or an agent run.

### Update or remove the deployment

| What changed | Command |
| --- | --- |
| Code | `./scripts/railway/redeploy.sh` |
| Production settings | `./scripts/railway/env-sync.sh` |
| Both | Run `env-sync.sh --no-deploy`, then `redeploy.sh` |
| View logs | `railway logs --service agent-os` |
| Delete the project | `./scripts/railway/down.sh` |

**Deleting the project deletes its database and all its data.** Local env files are
kept; review their saved URL and authentication settings before creating a new project.

Removing a line from `.env.production` does not remove it from Railway. Clear an
optional credential by setting it to an empty value, or remove it in Railway.
Changing the database password needs a separate database update.

## Verify and develop

Install [uv](https://docs.astral.sh/uv/), then set up and activate the Python environment.
If another environment is active, run `deactivate` first.

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
./scripts/validate.sh
python -m evals --tag smoke
```

The smoke tests check OS Manager's onboarding, diagnostics, and explanation of agent memory.
They use model calls and save results in the database, where you can review them in the UI.
Keep PostgreSQL running—even listing the tests needs a database connection.

Add your own cases in [evals/cases.py](evals/cases.py), or use
[/create-evals](.agents/skills/create-evals/SKILL.md). To save a report, add
`--json-output tmp/evals.json`. To run one case, use `--name CASE_NAME`.
Evals use your application's database and workspace; agents can call tools during a test.

Change dependencies in `pyproject.toml`, then run `./scripts/generate_requirements.sh`.
Commit the updated `requirements.txt` and rebuild the API and any sandbox image you use.
See [AGENTS.md](AGENTS.md) for the code layout and development conventions.

## Configuration

[example.env](example.env) lists the available settings. Start with `OPENAI_API_KEY`;
add the others when you need them.

| Setting | What it's for |
| --- | --- |
| `OPENAI_API_KEY` | OS Manager, embeddings, and Codex Engineer. |
| `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` | Claude Engineer. |
| `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` | Connect OS Manager to Slack. Set both. |
| `PARALLEL_API_KEY` | Optional key for web search; without it, the template uses keyless MCP access. |
| `JWT_VERIFICATION_KEY` or `JWT_JWKS_FILE` | Verify login tokens in production. |
| `AGENTOS_URL` | Public URL used by scheduled jobs and MCP. Railway setup saves it for you. |
| `MCP_CONNECT_SECRET` | Connect browser MCP clients. Railway setup generates it for you. |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_DATABASE` | PostgreSQL connection settings. Local Compose configures these for you. |
| `RUNTIME_ENV` | `prd` by default. Local Compose uses `dev`, which disables token checks. |

<details>
<summary>Upgrading an existing deployment</summary>

This version replaces the old template-owned manager and workflows with Agno's
OS Manager and Company. Saved database records are kept when you upgrade.

Before deploying:

- Disable old `deployment-check` and `run-evals` schedules, whose workflows have been removed.
- Disable or update schedules that use `company-analyst`, including Release intake,
  Daily refresh, Weekly summary, and Weekly review.
- Check saved Studio components for references to removed functions, tools, or knowledge
  bases. Restore what they need or update them before use. Existing product knowledge is kept.
- Check the AgentOS Product's saved settings, owner, Sources, and maintenance schedule.
  Its ID is still `this-agentos`. Code declarations do not overwrite saved edits.
- Remove `ENABLE_MAINTENANCE`, `SANDBOX_ENABLED`, `SANDBOX_IMAGE`, and `SANDBOX_RUNTIME_ARN`
  from env files. Select a sandbox in `app/sandbox.py`; return `None` to turn it off.
  Railway scripts reject nonempty values for the retired sandbox settings.

Keep historical conversations, notes, and Company work. Update old references rather
than deleting the data they belong to.

</details>

## Learn more

- [Agno documentation](https://docs.agno.com)
- [Agno on GitHub](https://github.com/agno-agi/agno)
- [AgentOS UI](https://os.agno.com)
