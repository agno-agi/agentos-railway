# Run engineers in a sandbox

By default, engineers work in the project folder on the AgentOS server. A sandbox
runs them in a separate environment with its own copy of your repository.
Choose Docker for local development or AWS AgentCore for a hosted sandbox.

Follow the [platform setup](../README.md#run-locally) first. Run the commands below
from the repository root. The engineers still need their model credentials:
`OPENAI_API_KEY` for Codex, and `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` for Claude.
Their models are configured in [agents/engineers.py](../agents/engineers.py).

## Choose your repository

In [app/sandbox.py](../app/sandbox.py), set `REPOSITORY` to your own repo and branch:

```python
REPOSITORY = Repository("https://github.com/YOUR-ORG/YOUR-REPO", branch="main")
```

## Local Docker sandbox

Set `sandbox_provider()` to return `docker_sandbox()`. Update `REPOSITORY` to your
GitHub repository and branch. The sandbox checks out that repository.

Run the API on your computer so it can reach Docker. Install [uv](https://docs.astral.sh/uv/)
and configure `.env` using the [local setup instructions](../README.md#run-locally).
If a Python environment is active, run `deactivate` first.

```sh
docker compose up -d agentos-db
./scripts/venv_setup.sh
docker build --target sandbox --load -t agno-sandbox:local .
docker compose stop agentos-api
RUNTIME_ENV=dev DB_HOST=127.0.0.1 DB_PORT=5432 \
  AGENTOS_URL=http://127.0.0.1:8000 \
  uv run --no-project --env-file .env --with-requirements requirements.txt \
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload \
  --reload-dir agents --reload-dir app --reload-dir db --reload-dir evals
```

Keep that terminal running. From another terminal, check the API's MCP connection:

```sh
MCP_CHECK_HOST=1 ./scripts/mcp_check.sh
```

Checkpoints are saved in `tmp/checkpoints`. Agno passes the engineers' model credentials
to the sandbox. For a private repository, also supply `GITHUB_READ_TOKEN` through the
provider's `env` mapping. Read its value from your environment or secret store;
never put the token itself in code. Git push credentials need separate configuration.

## AWS AgentCore sandbox

Build an ARM64 sandbox image, using your ECR image URL and tag:

```sh
SANDBOX_ECR_IMAGE=YOUR-ECR-URI:YOUR-TAG
docker build --target sandbox --platform linux/arm64 --load -t "${SANDBOX_ECR_IMAGE}" .
```

Push the image to ECR, then create an AgentCore runtime and execution role with your
AWS tools. Set `sandbox_provider()` to return `agentcore_sandbox("your-runtime-arn")`.
Update `REPOSITORY` to your repository and branch. The API host needs AWS credentials;
the runtime ARN determines the region. It does not need a Docker daemon.

The API also needs a persistent volume mounted at `/data` to save checkpoints.
Follow your template's [deployment instructions](../README.md#sandbox-storage) to
configure that storage before enabling AgentCore. Keep one API replica. The
application refuses to use AgentCore without the `/data` mount.

To use Claude through Bedrock, add `CLAUDE_CODE_USE_BEDROCK="1"` and an explicit
`AWS_REGION` to the `AgentCoreSandbox` provider's `env` mapping. Give its execution role
access to the model, and set Claude's model to a supported Bedrock inference profile.
These settings are not copied from the host automatically. For a private repository,
supply `GITHUB_READ_TOKEN` through the same mapping, reading it from your secret store.

## Company Tasks

Before using a sandbox for Company Tasks, check that the Product's saved Git Source
matches `REPOSITORY.url`. Keep its local source too, so Company can read the files.
Test an engineer run and a Company Task through completion on your deployment;
a successful API startup does not prove either one works.
