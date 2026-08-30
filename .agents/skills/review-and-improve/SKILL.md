---
name: review-and-improve
description: Repo-wide drift sweep for public-readiness — diff docs against code, confirm every agent is registered and reachable, every env var documented, every doc path exists, and scripts behave as advertised; auto-fix mechanical drift and flag the rest. Use before a public release or after a refactor.
---

# Review and Improve

> _Coding-agent workflow: run as `/review-and-improve` or by describing the task._

Sweep the repo for docs accuracy, reachability, and consistency. Fix mechanical drift in place; surface the rest. [`AGENTS.md`](../../../AGENTS.md) is the source of truth (`CLAUDE.md` symlinks to it).

**Auto-fix:** stale doc paths; `example.env` entries missing for vars the code reads, or stale ones nothing reads (keep those a comment marks optional/future); a registered agent or workflow missing from an architecture diagram; an agent file on disk not imported in `app/main.py`; a missing `app/config.yaml` manifest entry (draft one and flag it); broken links between docs and skills; a single-line claim in one doc contradicted by another doc or by code (fix the doc).

**Flag, don't fix:** section-level rewrites; code beyond imports; `pyproject.toml`; anything in `db/`, `compose.yaml`, `Dockerfile`; failing evals or live agents.

## 0. Preconditions

`curl -sSf http://localhost:8000/health` returns 200 (Step 4 needs it). Suggest `git checkout -b review/$(date +%Y%m%d)`.

## 1. Scope

Restate in a few lines: `README.md`, `AGENTS.md`, `example.env`; `.agents/skills/*/SKILL.md`; `app/`, `agents/`, `teams/`, `workflows/`, `db/`, `evals/`, `scripts/`; `compose.yaml`, `Dockerfile`, `pyproject.toml`, `railway.json`. Skip `.venv/`, caches, `.git/`. Fold in any concern the user names.

## 2. Inventory

Read first, fix once. Build the picture: registered agents/teams/workflows in `app/main.py`; files on disk; what [`app/registry.py`](../../../app/registry.py) declares and imports; env vars read (`getenv(`, `os.environ`, plus `env_flag`/`_int_env` helpers); the manifest; eval cases; `register_schedules()` targets; what each script does.

## 3. Consistency pass

| Check | Where |
|---|---|
| Every agent/team/workflow file is registered | `agents/`, `teams/`, `workflows/` ↔ `app/main.py` |
| Every registered component has a manifest entry | `app/main.py` ↔ `app/config.yaml` |
| Every env var in code is documented, and every documented var is read | code ↔ `AGENTS.md` table ↔ `example.env` (`RUNTIME_ENV` is deliberately absent from `example.env`) |
| Every path and script named in docs exists and does what's claimed | `README.md`, `AGENTS.md`, skills ↔ filesystem |
| Architecture diagram matches registrations | `AGENTS.md` |
| Eval cases reference real agents and tools | `evals/cases.py` |
| Every schedule hits a real workflow id | `app/schedules.py` ↔ `workflows/` |
| Registry inventory prose matches `app/registry.py` | `AGENTS.md` |
| Key Files table matches the tree | `AGENTS.md` |
| Skill `name:` equals its folder; `../../../` links resolve; `.claude/skills` symlink resolves | `.agents/skills/` |
| `.mcp.json` servers agree with the docs | `.mcp.json` |
| MCP endpoint claims match `mcp_server=` in `app/main.py`; `scripts/mcp_check.sh` calls a registered agent | docs ↔ code |

## 4. Live smoke

Confirm the container serves *this* repo's components (code components are `is_component=false`):

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | select(.is_component == false) | .id' | sort
curl -s http://localhost:8000/teams  | jq -r '.[] | select(.is_component == false) | .id' | sort
```

A mismatch with `app/main.py` means another checkout owns port 8000 — stop and say so.

Smoke every code agent and the team with one quick prompt each (`/agents/<slug>/runs`, `/teams/agno/runs`; `user_id=claude-review`, `stream=false`). Pass = 200, non-empty content, no errors in `docker logs agentos-api --since 30s`. Bracket the whole step with the learning snapshot pair, and `platform-builder`'s run with the builder pair ([improve-agent Step 2](../improve-agent/SKILL.md)); use only the builder's first quick prompt (the others build real components). Workflows stay out — `deployment-check` runs on its cron, `run-evals` spends model budget.

Then `./scripts/mcp_check.sh` → `MCP OK — <n> tools` and a real answer.

Quality issues are out of scope — note them and point at [`improve-agent`](../improve-agent/SKILL.md).

## 5. Format + validate

```bash
source .venv/bin/activate
./scripts/format.sh && ./scripts/validate.sh
```

Surface validate errors verbatim.

## 6. Evals

Ask first (hits OpenAI, 1–3 minutes): `python -m evals --tag release`. Failures go to "Needs your call" with [`eval-and-improve`](../eval-and-improve/SKILL.md) as the follow-up.

## 7. Report

Nothing fixed or flagged → *"Repo is consistent and the live container is healthy. No follow-up needed."* Otherwise: **Fixed automatically** (one line per change, with path); **Needs your call** (ranked, with recommended action); `git diff --stat` and a suggested commit (`chore: review-and-improve sweep` + a bullet per bucket).
