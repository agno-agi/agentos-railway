---
name: review-and-improve
description: Review this AgentOS repository for public readiness after a refactor or before release. Compare documentation, skills, configuration, component wiring and scripts with the implementation; fix clear documentation drift when requested and report behavioral issues with evidence. Use for a repository consistency sweep, not agent-quality tuning or deployment.
---

# Review and Improve

Review the requested scope against [AGENTS.md](../../../AGENTS.md) and the actual
implementation. When comparing with a branch or PR, record the base and head SHAs,
and distinguish committed changes from local edits. A review-only request stays read-only.
For a review-and-improve request, correct clear documentation and link errors within scope;
report behavior changes separately unless the user has authorized their repair.

## 1. Establish the scope

Inspect the working tree before editing and preserve concurrent changes. Review the named
files first. A repository-wide pass covers `README.md`, `AGENTS.md`, `example.env`, skills,
`app/`, `agents/`, `teams/`, `db/`, `evals/`, `scripts/`, and build/deployment configuration.
Include user-added workflows or other directories when present. Exclude environments,
caches, generated files and Git internals from content scans. Do not print env-file values.

A running API is not required for the source review. Establish whether development uses
Compose or the host API before attempting runtime checks; use the matching README commands.
If a runtime is unavailable or belongs to another checkout, continue the source review and
report the runtime verification gap.

## 2. Compare declarations, documentation and behavior

| Check | Evidence |
|---|---|
| Application agents and teams are deliberately registered, with stable IDs | Source declarations, `app/main.py`, `app/config.yaml` |
| Framework-owned components stay in Agno | `OSManager(...)`, `CompanyConfig(...)`, installed framework source |
| Shared resources and Studio capabilities match documentation | `app/registry.py`, `db/`, AgentOS registration |
| Configuration names, defaults and prerequisites agree | Environment reads, `example.env`, README, Compose, deployment scripts |
| Documented commands and file paths work | Scripts, skills, CLI help and installed signatures |
| Skills remain discoverable and their routing is coherent | Frontmatter, relative links, `.claude/skills`, `CLAUDE.md` |
| Eval targets, tool names and CLI examples exist | `evals/cases.py`, `evals/__main__.py`, installed Agno eval APIs |
| Sandbox documentation matches execution and persistence requirements | `app/sandbox.py`, `agents/engineers.py`, Dockerfile, README |
| MCP claims match the exposed interface and authentication behavior | `app/interfaces.py`, `app/main.py`, `scripts/mcp_check.sh` |

Do not register every file found under `agents/` or invent manifest entries for internal
components: determine whether it is an intended public component, a helper or framework-owned.
OS Manager, its members and Company Manager are framework-owned; do not restore
the old application-owned manager/builder/engineer stack. OS, Company and queue storage
reuse `get_postgres_db()`; knowledge content adapters have distinct IDs.

`app/company.py` declares `agentos-maintenance`: Company Manager reviews releases and
the codebase on a daily 09:00 UTC schedule and proposes up to three Backlog Tasks.
New Routines are disabled until enabled in the UI; automatic acceptance is also off.
Existing saved enabled/paused state is preserved. Verify the declaration against saved
schedule state; do not infer successful execution from its presence. Before removing
or renaming a component in an existing deployment, inspect saved schedules and Studio
references read-only when access is available. Source absence does not establish that
a saved record is absent. Preserve historical sessions, notes and Company records.

## 3. Verify proportionately

Use static checks first:

```sh
source .venv/bin/activate
./scripts/validate.sh
git diff --check
```

For shell changes, run `bash -n` on the affected scripts. After authorized edits, format
only as needed and inspect the resulting diff. Use disposable local fixtures to reproduce
script failures when useful; keep the starter free of a bundled regression-test suite.
CLI help and mock fixtures do not establish successful cloud deployment.

For an available local API, verify `/health` and the relevant component listing using its
configured authentication. Confirm the process or container serves this checkout before
drawing conclusions. Run `scripts/mcp_check.sh` in Compose mode, or
`MCP_CHECK_HOST=1 ./scripts/mcp_check.sh` for the host API. The default MCP check proves
initialization and required tool availability, not an agent answer.

Run model probes or evals only within the user's authorized scope and budget. Inspect
available cases before selecting a tag; do not assume `release` or `live` cases exist.
Even eval CLI help/list commands import knowledge storage and require PostgreSQL; inspect
`evals/cases.py` directly when the database is unavailable.
Evals use the application's database and persist sessions and results. Use explicitly owned
fixtures for mutating cases; do not restore snapshot-diff cleanup or delete historical data.
Do not smoke every coding agent automatically: those runs can execute code and modify workspaces.
HTTP availability, direct execution, delegation and Company Task completion are separate checks.

## 4. Report

Lead with actionable findings: severity, file and line, triggering condition, observed or
source-backed consequence, and recommended fix. Label inherited issues separately from
regressions against the comparison base. Explain what was corrected and what remains.
Give a sharing or merge recommendation limited to the reviewed scope.

Record verification in `tmp/VERIFY.md` when making changes, separating static,
deterministic, model, container and hosted results. Report skipped checks and their limits;
do not equate a passing linter or mock fixture with a healthy deployed platform.

Route agent behavior changes to [extend-agent](../extend-agent/SKILL.md), missing eval
coverage to [create-evals](../create-evals/SKILL.md), eval failures and agent hardening to
[improve](../improve/SKILL.md), and an explicitly requested deployment
to [deploy-platform](../deploy-platform/SKILL.md).
