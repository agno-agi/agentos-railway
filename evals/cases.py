"""Application smoke checks. Run with python -m evals."""

from agno.eval import Case

from app.main import agent_os

CASES = (
    Case(
        name="manager_explains_application",
        team=agent_os.manager,
        input="Read README.md. Explain how to start this application, talk to OS Manager and add an agent. "
        "Do not create or change anything.",
        criteria="Give actionable startup instructions grounded in README.md, including .env and OPENAI_API_KEY "
        "configuration, the startup command, a documented way to chat with OS Manager, and how to add an agent. "
        "Do not claim to have started the application or created an agent.",
        expected_tool_calls=("read_file",),
        tags=("smoke",),
    ),
    Case(
        name="manager_checks_health",
        team=agent_os.manager,
        input="Run diagnostics and report this AgentOS's health. Do not change any state or run other components.",
        criteria="Report the observed diagnostics accurately, including any problems. Do not present a "
        "configuration/database check as proof that agents executed or that production is healthy.",
        expected_tool_calls=("run_diagnostics",),
        tags=("smoke",),
    ),
    Case(
        name="manager_explains_configured_learning",
        team=agent_os.manager,
        input="Read app/registry.py. What learning is configured in this app, and does it retrain the model? "
        "Do not change anything.",
        criteria="Explain that app/registry.py configures shared_learning as a LearningMachine backed by "
        "PostgreSQL, with user profiles and user memories in AGENTIC mode. It persists information outside "
        "model weights and does not retrain the model. Ground claims in the file; do not invent additional "
        "enabled stores or claim a successful live learning test.",
        expected_tool_calls=("read_file",),
        tags=("smoke",),
    ),
)
