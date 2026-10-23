"""Optional Docker and AgentCore sandboxes."""

from pathlib import Path

from agno.sandbox import Repository, Sandbox
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandbox

# Set to Repository("https://github.com/YOUR-ORG/YOUR-REPO", branch="main") before enabling a sandbox.
REPOSITORY: Repository | None = None
LOCAL_CHECKPOINTS = Path(__file__).resolve().parents[1] / "tmp" / "checkpoints"
PRODUCTION_VOLUME = Path("/data")


def sandbox_provider() -> Sandbox | None:
    """Choose None, docker_sandbox(), or agentcore_sandbox("your-runtime-arn")."""
    return None


def docker_sandbox() -> DockerSandbox:
    return DockerSandbox(
        image="agno-sandbox:local",
        network="isolated",
        workspace_mb=2048,
        checkpoints=FileCheckpointStore(LOCAL_CHECKPOINTS),
    )


def agentcore_sandbox(runtime_arn: str) -> Sandbox:
    from agno.sandbox.agentcore import AgentCoreSandbox

    if not PRODUCTION_VOLUME.is_mount():
        raise ValueError(f"Mount a persistent volume at {PRODUCTION_VOLUME} before enabling AgentCore")
    return AgentCoreSandbox(
        runtime_arn=runtime_arn,
        checkpoints=FileCheckpointStore(PRODUCTION_VOLUME / "checkpoints"),
    )
