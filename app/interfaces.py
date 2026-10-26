"""Reach OS Manager through MCP and, when configured, Slack."""

from os import getenv

from agno.os import AgentOS, AgentOSBuiltinAuth, MCPConfig


def mcp_auth(agentos_url: str) -> AgentOSBuiltinAuth | None:
    """Enable MCP OAuth when the MCP_CONNECT_SECRET is provided."""
    secret = getenv("MCP_CONNECT_SECRET")
    if not secret:
        return None
    return AgentOSBuiltinAuth(url=agentos_url, secret=secret)


def attach_interfaces(agent_os: AgentOS) -> None:
    """Publish OS Manager alongside the built-in MCP tools; optionally attach Slack."""
    manager = agent_os.manager
    if manager is None:
        raise RuntimeError("OS Manager must be configured before attaching interfaces.")
    agent_os.mcp = MCPConfig(
        tools=[
            manager.as_tool(
                name="os_manager",
                title="OS Manager",
                description="Talk to OS Manager of this AgentOS. Pass session_id back to continue the conversation.",
            )
        ],
        default_tools=True,
    )
    token, secret = getenv("SLACK_BOT_TOKEN"), getenv("SLACK_SIGNING_SECRET")
    if token and secret:
        from agno.os.interfaces.slack import Slack

        agent_os.interfaces.append(
            Slack(
                team=manager,
                token=token,
                streaming=True,
                signing_secret=secret,
                resolve_user_identity=True,
                loading_text="Pulling the thread...",
            )
        )
