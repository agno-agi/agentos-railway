# Run coding agents on AgentOS

Your platform includes **Claude Engineer** (Claude Code) and **Codex Engineer** agents.
Enable coding agents to explore code, build features, run checks, and open pull
requests once you configure GitHub access.

Start with this platform's repository, use another project, or add a coding-agent
pair for each repository. First enable an agent, then choose a sandbox for isolation
and checkpoint recovery.

## Enable a coding agent

The included agents are disabled by default. For a public deployment, complete JWT
setup before enabling them.

1. Add `ANTHROPIC_API_KEY` for Claude or `OPENAI_API_KEY` for Codex to `.env` locally
   or your hosted environment settings.
2. In [app/main.py](../app/main.py), uncomment the matching import from
   `agents.engineers` and factory call in the `agents` list. Keep your other agents.
3. Run `./scripts/format.sh`, rebuild and deploy, then open the agent in AgentOS.

Try:

> Explain this project and suggest three improvements to its agents. Don't change any files yet.

[agents/engineers.py](../agents/engineers.py) defines their models and harness options.
To disable an agent, comment out its import and factory call and redeploy.

## Sandboxes and checkpoints

Without a sandbox, coding agents run directly on the API host with access to its
files, commands, and environment. Use that mode with trusted users.

A sandbox gives each coding session its own environment and repository checkout.
Checkpoints save its files and native coding session for recovery.
Choose **Docker for local development** or **AgentCore for a hosted platform**.

In [app/sandbox.py](../app/sandbox.py), enable sandboxes and set the repository and
branch. Use your copy of this platform or another project:

```python
SANDBOX_ENABLED = True
REPOSITORY = Repository("https://github.com/YOUR-ORG/YOUR-REPO", branch="main")
```

Both included coding agents use this repository. Start a new conversation after
changing it. For private repositories, configure [GitHub access](#publish-changes-to-github).
The repository setting only applies when sandboxes are enabled.

Complete the backend setup below before deploying this change. Compose selects
`SANDBOX_PROVIDER=docker`; select `agentcore` in your hosted deployment settings.
See your repository's [deployment instructions](../README.md#deploy-in-production).
`RUNTIME_ENV` still controls JWT authorization independently.

### Local Docker sandbox

Configure `.env` using the [local setup instructions](../README.md#run-locally).
From the repository root, build the sandbox image and start the platform:

```sh
docker build --target sandbox --load -t agno-sandbox:local .
docker compose up -d --build
./scripts/mcp_check.sh
```

The first command builds and loads the Dockerfile's `sandbox` stage. The API runs in
Compose and starts separate containers from that image for coding sessions.
Rebuild the sandbox image when its dependencies or Dockerfile change.

Compose gives the API access to your Docker daemon through its socket. Use this for
trusted local development; coding sandboxes receive no socket. Checkpoints persist
in the project's `tmp/checkpoints` folder while those files remain.

Model credentials are forwarded automatically. For private repositories and publishing,
configure [GitHub access](#publish-changes-to-github).

### AWS AgentCore sandbox

Your API stays on its current host (Render). AgentCore runs coding sessions, and S3 stores
their checkpoints. Run [scripts/aws.py](../scripts/aws.py) locally to set this up.
It creates the runtime, image repository, checkpoint bucket, and required IAM identities.

#### 1. Configure AWS

You need Docker with ARM64 build support and an AWS profile that can manage
CloudFormation, ECR, AgentCore, S3, IAM, CloudWatch Logs, and X-Ray. These provisioning
permissions stay on your computer; the hosted API uses separate credentials.
Prepare your Python environment. If this repository's `.venv` is already active,
skip these commands. If another environment is active, run `deactivate` first:

```sh
./scripts/venv_setup.sh
source .venv/bin/activate
```

Add your profile to the existing `.env` (copy [example.env](../example.env) if needed):

```dotenv
AWS_PROFILE=your-profile
AWS_REGION=us-east-1
```

For SSO, use [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
to configure the profile with `aws configure sso`, then sign in:

```sh
aws sso login --profile your-profile
```

Preview the account, region, and resource names:

```sh
scripts/aws.py plan
```

`plan` verifies your AWS identity and shows the current tracing configuration without
changing anything. Check the account and region before continuing.

<details>
<summary>Optional setup settings</summary>

The script reads `.env`; exported variables take precedence. Omit `AWS_PROFILE` to
use default AWS credentials. Region precedence is `AWS_REGION`, `AWS_DEFAULT_REGION`,
profile region, then `us-east-1`.

| Variable | Default |
| --- | --- |
| `DEPLOYMENT_NAME` | `agentos-sandbox` |
| `BUCKET_NAME` | Derived from deployment name, account, and region. |
| `CHECKPOINT_PREFIX` | `agentos/checkpoints/` |

Keep credentials in your AWS profile and account-specific settings out of Git.

</details>

#### 2. Create the resources

```sh
scripts/aws.py apply
```

This creates two CloudFormation stacks, builds and uploads the ARM64 sandbox image,
and waits for the runtime and endpoint to be ready. It also configures runtime trace
delivery and enables [CloudWatch Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)
if needed. Transaction Search is shared by the AWS account and region; existing
indexing settings and configured runtime trace delivery are preserved.
Resources and telemetry incur AWS charges.

Wait for **Sandbox resources are ready**, then keep the printed settings for the
next steps. To retrieve them again, run `scripts/aws.py status`.

#### 3. Create credentials for your API

Your local profile provisions resources. The script creates a separate
`ApplicationUser` with access to the runtime and checkpoint storage for your API.

In the AWS console:

1. Open **IAM → Users** and select the printed `ApplicationUser`.
2. Open **Security credentials → Create access key**.
3. Choose the use case for an application running outside AWS and save the key securely.

Use this application's key on your API host. Keep your provisioning credentials local.
If your API already uses an AWS workload role, grant it the application user's scoped
policy instead; the runtime's execution role is a separate identity.

#### 4. Connect and deploy

In your API host's environment settings using your deployment instructions, add:

| Variable | Value |
| --- | --- |
| `SANDBOX_PROVIDER` | `agentcore`. |
| `AWS_ACCESS_KEY_ID` | The application user's access key ID. |
| `AWS_SECRET_ACCESS_KEY` | Its secret access key. |
| `AWS_REGION` | The region printed by the script. |
| `AGENTCORE_RUNTIME_ARN` | The printed runtime ARN. |
| `AGENTCORE_CHECKPOINT_BUCKET` | The printed checkpoint bucket. |
| `AGENTCORE_CHECKPOINT_PREFIX` | The printed checkpoint prefix. |

Keep production JWT authorization, database settings, and your agents' model keys.
Agno forwards model credentials to the sandbox. For IAM user keys, remove stale
`AWS_PROFILE` or `AWS_SESSION_TOKEN` settings from the hosted API.

Confirm sandboxes and the repository are configured in `app/sandbox.py`, and the
coding agents are enabled in `app/main.py`. Push any code changes to your deployment
branch, then save the environment settings and redeploy using your host's
deployment instructions. No Docker daemon or persistent API disk is needed for AgentCore.

#### 5. Try a coding agent

Once the API is healthy, select your deployed platform in AgentOS and start a new
conversation with an enabled coding agent:

> Show the current repository and branch. Create sandbox-check.txt containing
> "AgentCore is working", then read it back. Do not commit or push anything.

Confirm the run completes, uses the expected repository, and reads back the file.
Repeat for each enabled agent. If it fails, inspect the run error and API logs;
runtime startup errors are in CloudWatch. A healthy API alone does not prove execution.

<details>
<summary>View runtime traces</summary>

After running a coding session, open **AgentCore → Observability** in the same AWS
region and select your sandbox runtime. After first enabling Transaction Search,
allow about 10 minutes for traces to become searchable.

`scripts/aws.py status` shows whether Transaction Search is active and runtime trace
delivery is configured. This confirms configuration, not that traces have arrived.
Use CloudWatch for runtime logs and metrics, and AgentOS for your agent's runs.
These AWS traces describe runtime activity; model calls and coding-tool spans need
additional instrumentation and are not enabled by this script.

</details>

<details>
<summary>Verify checkpoint recovery</summary>

After the test turn finishes and its checkpoint is saved, replace the API instance
and stop the test's AgentCore runtime session. Continue the **same conversation as
the same user** and ask it to read `sandbox-check.txt` without recreating it.
Verify the file and native coding session are restored.

Restarting only the API can reconnect to a live sandbox, so it does not prove recovery.
Checkpoints restore the last saved state, not unfinished edits or running processes,
and cannot undo external actions such as Git pushes.

Keep the bucket private, preserve active checkpoints, and use the same bucket/prefix
across this platform's API replicas.

</details>

<details>
<summary>Update or troubleshoot AWS resources</summary>

Run `scripts/aws.py apply` again after changing sandbox dependencies or the Dockerfile.
Keep resource names and the checkpoint prefix stable. Updating the API alone does not
update the AgentCore image.

If provisioning fails, inspect the named stack's **Events** in CloudFormation before
retrying. The script rejects unrelated stacks and storage replacements. For runtime
access errors, compare the API's region, ARN, credentials, and bucket with
`scripts/aws.py status`.

</details>

<details>
<summary>Remove the AWS resources</summary>

Disable the coding agents and redeploy first. Delete the application's access keys
in IAM, then delete the `<DEPLOYMENT_NAME>-runtime` stack followed by
`<DEPLOYMENT_NAME>-foundation` in CloudFormation.

S3 checkpoints and ECR images are retained. Empty and delete them separately when no
longer needed; CloudWatch logs may also remain. The runtime stack deletes trace
resources it created. Existing external trace delivery and the shared Transaction
Search setting and log policy are left in place because other workloads may use them.
Retained resources and telemetry can incur charges.

</details>

## Publish changes to GitHub

Git and the GitHub CLI are included in both the API and sandbox images. Create a
[fine-grained personal access token](https://github.com/settings/personal-access-tokens/new):

1. Give it a name such as **AgentOS** and choose an expiration date.
2. Set **Resource owner** to the user or organization that owns the repository.
3. Under **Repository access**, choose **Only select repositories** and select the
   repositories your coding agents should work on.
4. Under **Repository permissions**, set **Contents** and **Pull requests** to
   **Read and write**. Leave other permissions at their defaults.
5. Generate the token. If the organization requires approval, have an owner approve
   it before using it for private access or publishing.
6. Copy it into `GH_TOKEN` in `.env` locally or your API host's environment settings.
   Keep it out of source code and agent prompts.

The token acts as your GitHub user and cannot grant access you don't already have.
If the agent must edit `.github/workflows`, also grant **Workflows: Read and write**.

The template forwards the token to coding sandboxes and configures Git to authenticate
through `gh`. The same token supports private checkout; set `GITHUB_READ_TOKEN` only
if you want a separate checkout credential. No interactive GitHub login is needed.

Commits default to `AgentOS <agentos@localhost>`. To use your own identity, set
`GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL`.
These settings are also forwarded to sandboxes. For different repository credentials,
pass overrides through the provider's `env` argument.

Redeploy the API after changing environment settings and start a new coding conversation.
When upgrading an older sandbox image, rebuild it locally or run `scripts/aws.py apply`
for AgentCore once. Later token changes do not require rebuilding the image.

Try:

> Make a small improvement on a new branch, run the relevant checks, and open a pull
> request. Do not merge it.

Review the PR before scheduling improvement work. In direct mode, the deployed API
image has no `.git` directory; ask the agent to clone the repository into a separate
writable directory first. Sandbox sessions already have their repository checkout.

## Add agents for more repositories

You can run several Claude and Codex agents on the same platform: a pair for the
platform, another for your website, and another for your backend. Give each agent a
unique ID and its own repository configuration.

The included factories have fixed IDs, so keep one instance of each. Configure a
sandbox before adding more agents.

<details>
<summary>Example: one Claude/Codex pair per repository</summary>

Create `agents/repositories.py`:

```python
from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.sandbox import Repository

from app.sandbox import sandbox_provider
from db import get_postgres_db

sandbox = sandbox_provider()
if sandbox is None:
    raise ValueError("Configure a sandbox in app/sandbox.py first.")
db = get_postgres_db()


def create_repository_agents(slug: str, url: str, branch: str = "main"):
    repository = Repository(url, branch=branch)
    return [
        ClaudeAgent(
            id=f"{slug}-claude",
            name=f"{slug.title()} Claude",
            model="claude-opus-5-5",
            db=db,
            sandbox=sandbox,
            repository=repository,
            system_prompt={"type": "preset", "preset": "claude_code"},
            permission_mode="acceptEdits",
        ),
        CodexAgent(
            id=f"{slug}-codex",
            name=f"{slug.title()} Codex",
            model="gpt-6.1-sol",
            db=db,
            sandbox=sandbox,
            repository=repository,
            sandbox_mode="workspace-write",
        ),
    ]
```

In `app/main.py`, import `create_repository_agents` from `agents.repositories` and
add these entries to the existing `AgentOS` agent list, preserving your other agents:

```python
agents=[
    # Keep your existing agents here.
    *create_repository_agents("platform", "https://github.com/YOUR-ORG/agent-platform"),
    *create_repository_agents("website", "https://github.com/YOUR-ORG/website"),
],
```

This adds **Platform Claude**, **Platform Codex**, **Website Claude**, and **Website Codex**.
Remove either constructor if you only want one coding agent per repository. Add their
suggested prompts to [app/config.yaml](../app/config.yaml), then format and redeploy.

</details>

Each conversation has its own checkout and sandbox state. Share work through Git
commits and PRs. Scope GitHub credentials to the intended repositories; different
agent IDs do not restrict a shared token's access.

## Scaling

When you need multiple API instances, follow the [scaling guide](scaling.md) for
Redis and coordination across replicas.
