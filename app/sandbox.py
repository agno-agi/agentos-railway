"""Optional Docker and AgentCore sandboxes."""

from collections.abc import Mapping
from os import getenv
from pathlib import Path

from agno.sandbox import Repository, Sandbox
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox

SANDBOX_ENABLED = False
# Set your repository and branch before enabling sandboxes.
REPOSITORY: Repository | None = None
LOCAL_CHECKPOINTS = Path(__file__).resolve().parents[1] / "tmp" / "checkpoints"


def sandbox_provider() -> Sandbox | None:
    """Use the selected backend only when sandboxes are enabled in code."""
    if not SANDBOX_ENABLED:
        return None

    provider = getenv("SANDBOX_PROVIDER", "docker")
    if provider == "docker":
        return docker_sandbox()
    if provider == "agentcore":
        runtime_arn = getenv("AGENTCORE_RUNTIME_ARN", "").strip()
        checkpoint_bucket = getenv("AGENTCORE_CHECKPOINT_BUCKET", "").strip()
        if not runtime_arn or not checkpoint_bucket:
            raise ValueError("AgentCore requires AGENTCORE_RUNTIME_ARN and AGENTCORE_CHECKPOINT_BUCKET.")
        return agentcore_sandbox(
            runtime_arn=runtime_arn,
            checkpoint_bucket=checkpoint_bucket,
            checkpoint_prefix=getenv("AGENTCORE_CHECKPOINT_PREFIX", "agentos/checkpoints/"),
        )
    raise ValueError("SANDBOX_PROVIDER must be 'docker' or 'agentcore'.")


def docker_sandbox(env: Mapping[str, str] | None = None) -> DockerSandbox:
    return DockerSandbox(
        image="agno-sandbox:local",
        network="isolated",
        workspace_mb=2048,
        checkpoints=FileCheckpointStore(LOCAL_CHECKPOINTS),
        env=sandbox_env(env),
    )


def agentcore_sandbox(
    runtime_arn: str,
    checkpoint_bucket: str,
    checkpoint_prefix: str = "agentos/checkpoints/",
    env: Mapping[str, str] | None = None,
) -> Sandbox:
    from agno.sandbox.agentcore import AgentCoreSandbox
    from agno.sandbox.s3 import S3CheckpointStore

    return AgentCoreSandbox(
        runtime_arn=runtime_arn,
        checkpoints=S3CheckpointStore(
            bucket=checkpoint_bucket,
            prefix=checkpoint_prefix,
            region=getenv("AWS_REGION") or getenv("AWS_DEFAULT_REGION"),
        ),
        env=sandbox_env(env),
    )


def sandbox_env(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Pass GitHub access and commit identity to coding sessions."""
    names = (
        "GH_TOKEN",
        "GITHUB_READ_TOKEN",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    )
    values = {name: value for name in names if (value := getenv(name))}
    values.update(overrides or {})
    # Agno's repository checkout uses a separate variable from the GitHub CLI.
    if values.get("GH_TOKEN") and not values.get("GITHUB_READ_TOKEN"):
        values["GITHUB_READ_TOKEN"] = values["GH_TOKEN"]
    return values
