"""Optional Docker and AgentCore sandboxes."""

from pathlib import Path

from agno.sandbox import Repository, Sandbox
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox

# Set to Repository("https://github.com/YOUR-ORG/YOUR-REPO", branch="main") before enabling a sandbox.
REPOSITORY: Repository | None = None
LOCAL_CHECKPOINTS = Path(__file__).resolve().parents[1] / "tmp" / "checkpoints"


def sandbox_provider() -> Sandbox | None:
    """Choose None, docker_sandbox(), or agentcore_sandbox("runtime-arn", "checkpoint-bucket")."""
    return None


def docker_sandbox() -> DockerSandbox:
    return DockerSandbox(
        image="agno-sandbox:local",
        network="isolated",
        workspace_mb=2048,
        checkpoints=FileCheckpointStore(LOCAL_CHECKPOINTS),
    )


def agentcore_sandbox(
    runtime_arn: str, checkpoint_bucket: str, *, checkpoint_prefix: str = "agentos/checkpoints/"
) -> Sandbox:
    from agno.sandbox.agentcore import AgentCoreSandbox
    from agno.sandbox.s3 import S3CheckpointStore

    return AgentCoreSandbox(
        runtime_arn=runtime_arn,
        checkpoints=S3CheckpointStore(bucket=checkpoint_bucket, prefix=checkpoint_prefix),
    )
