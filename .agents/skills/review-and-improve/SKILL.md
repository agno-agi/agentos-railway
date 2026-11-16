---
name: review-and-improve
description: Review this AgentOS repository for public readiness after a refactor or before release. Compare documentation, skills, configuration, component wiring and scripts with the implementation; fix clear documentation drift when requested and report behavioral issues with evidence. Use for a repository consistency sweep, not agent-quality tuning or deployment.
---

# Review and Improve

Check that the repository does what it says. Compare the documentation, skills and
configuration with the code, fix clear documentation errors when asked to improve, and report
behavior problems with evidence. A review-only request changes nothing.

Read [`AGENTS.md`](../../../AGENTS.md) and `git status` first. When comparing with a branch or
PR, note the base and head commits.

## 1. Compare

Review the files the user named. For the whole repository, check that:

- Every agent and team in `agents/` and `teams/` that should be served is registered in
  `app/main.py` and described in `app/config.yaml`.
- README, `AGENTS.md`, `example.env` and the skills name files, commands, settings and
  defaults that exist and work.
- What the docs say about Studio, knowledge, learning and notes matches `app/registry.py`.
- Eval cases in `evals/cases.py` target agents and tools that exist.
- Sandbox, MCP and deployment docs match `app/sandbox.py`, `app/interfaces.py`,
  `compose.yaml`, `Dockerfile` and the provider deployment files listed in `AGENTS.md`.
- Skill links resolve and each skill hands off to the right next skill.

Super Agent, Platform Builder and Mini Agent belong to Agno; do not add application copies of
them. Before renaming or removing a component, check saved schedules and Studio references.

## 2. Verify

```sh
source .venv/bin/activate
./scripts/validate.sh
git diff --check
```

With the API running, also check `/docs` and `./scripts/mcp_check.sh`. Run evals or model
prompts only when the user asks; they spend model calls and save results. Do not run the
coding agents as a routine check, because they execute code.

## 3. Report

Lead with findings, most serious first: file and line, what triggers the problem, what
happens, and the fix. Separate problems that were already there from ones the change
introduced. Say what you corrected, what you checked and what you did not. When you changed
files, record the checks in `tmp/VERIFY.md`.

For follow-up work use [extend-agent](../extend-agent/SKILL.md) for behavior changes,
[create-evals](../create-evals/SKILL.md) for missing coverage,
[improve](../improve/SKILL.md) for failing evals and hardening, and
[deploy-platform](../deploy-platform/SKILL.md) for deployment.
