---
name: review-and-improve
description: Repo-wide drift sweep for public-readiness — diff docs against code, confirm every agent is registered and reachable, every env var documented, every doc path exists, and scripts behave as advertised; auto-fix mechanical drift and flag the rest. Use before a public release or after a refactor.
---

# Review and Improve

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/review-and-improve`) or describe the task and it triggers automatically._

You are sweeping the whole repo for public-consumption readiness — docs accuracy, every agent reachable, scripts that actually do what the docs claim, no stale env vars, format + validate clean. Most drift is mechanical (renamed file, missing entry in `example.env`, new agent not in the architecture diagram) and you fix it in place. The rest is a punch list you surface to the user.

[`AGENTS.md`](../../../AGENTS.md) is the source of truth for repo conventions; [`CLAUDE.md`](../../../CLAUDE.md) is a symlink to it — edit once, both update.

## What you auto-fix vs. what you flag

**Auto-fix in place** (no asking):

- Stale file paths in any doc.
- Missing entries in [`example.env`](../../../example.env) for env vars the code actually reads.
- Stale entries in `example.env` for vars nothing reads — delete unless the surrounding comment block describes them as optional/future ("alternate model providers", "future feature"). Flag instead of fixing if intent is unclear.
- Architecture diagram in `AGENTS.md` / `README.md` missing a registered agent or workflow.
- New agent file on disk not yet imported in [`app/main.py`](../../../app/main.py) (add the import + append to `agents=[...]`).
- Missing manifest entry in `app/config.yaml` for a component registered in `app/main.py` (draft a one-line description and three quick prompts from its `INSTRUCTIONS`; flag the new entries so the user can refine). Only code components — a Studio-built one carries its own description.
- Missing or wrong cross-links between docs and the coding-agent skills in [`.agents/skills/*/SKILL.md`](../../../.agents/skills/) (and between skills).
- Single-line factual claim in one doc contradicted by another doc or by code — auto-fix the doc, not the code.

**Flag, don't fix** (surface for the user):

- Section-level doc rewrites (a premise is now wrong).
- Code changes beyond imports (instructions, tools, model swaps).
- Dependency edits in [`pyproject.toml`](../../../pyproject.toml).
- Anything in [`db/`](../../../db/), [`compose.yaml`](../../../compose.yaml), or [`Dockerfile`](../../../Dockerfile).
- Failing eval cases or failing live agents — recommend the right follow-up prompt; don't fix here.

## 0. Preconditions

- Live container reachable: `curl -sSf http://localhost:8000/health` returns 200. If not, ask the user to `docker compose up -d --build` first — Step 4 needs a live container. (`docker compose ps` is unreliable from worktrees or alternate clones — trust the health probe.)
- Recommend a feature branch so auto-fixes are easy to revert: `git checkout -b review/$(date +%Y%m%d)`.

## 1. Scope check

Restate the surface area in 4-5 lines so the user can redirect before you read everything:

- Top-level docs: [`README.md`](../../../README.md) (including its setup prompt), [`AGENTS.md`](../../../AGENTS.md), and [`example.env`](../../../example.env).
- Coding-agent skills: [`.agents/skills/*/SKILL.md`](../../../.agents/skills/).
- Code: [`app/`](../../../app/), [`agents/`](../../../agents/), [`teams/`](../../../teams/), [`workflows/`](../../../workflows/), [`db/`](../../../db/), [`evals/`](../../../evals/), [`scripts/`](../../../scripts/).
- Configs: [`compose.yaml`](../../../compose.yaml), [`Dockerfile`](../../../Dockerfile), [`pyproject.toml`](../../../pyproject.toml), [`railway.json`](../../../railway.json).

Skip: `.venv/`, `*_cache/`, `.git/`, anything generated.

If the user has a specific concern (recent refactor, prepping a public release, a doc they think is stale), fold it in now.

## 2. Inventory

Read every file in scope. Build a mental model of:

- **Registered agents + team** — what's imported in `app/main.py`'s `agents=[...]` and `teams=[...]`? This is the whole population this sweep is responsible for. Components the Studio built at runtime have no source file, no manifest entry, and no place in a docs diff.
- **Agent and team files on disk** — what's in [`agents/`](../../../agents/) and [`teams/`](../../../teams/)?
- **Registry blocks** — what [`app/registry.py`](../../../app/registry.py) declares (tools, functions, knowledge, learning, models, dbs, agents), and which modules it imports them from ([`app/knowledge.py`](../../../app/knowledge.py), [`app/learning.py`](../../../app/learning.py), [`app/notes.py`](../../../app/notes.py), [`app/functions.py`](../../../app/functions.py)).
- **Env vars actually read** — grep `os.environ`, `os.getenv`, `getenv(`, plus settings/config modules.
- **Manifest** — what's in [`app/config.yaml`](../../../app/config.yaml) under `manifest` (description + quick prompts per component)?
- **Eval cases** — what's in [`evals/cases.py`](../../../evals/cases.py)?
- **Registered workflows** — what's imported into [`app/main.py`](../../../app/main.py) and passed to `AgentOS(workflows=[...])`? Workflow files on disk in [`workflows/`](../../../workflows/)?
- **Schedules** — what `register_schedules()` ([`app/schedules.py`](../../../app/schedules.py)) registers: the env gate where one exists (`ENABLE_DEPLOY_CHECK`), and run-evals' ships-disabled posture (its enabled bit is user-owned via the AgentOS UI after first creation).
- **Scripts** — for each file in [`scripts/`](../../../scripts/), what does it actually do? (Headers and the first few lines are usually enough.)

Don't write anything yet — read first, fix once.

## 3. Consistency pass

The bulk of the work. Diff each pair below; auto-fix per the rules at the top.

| Check | Where | Common drift |
|---|---|---|
| Every agent + team file is registered | [`agents/`](../../../agents/), [`teams/`](../../../teams/) ↔ `app/main.py` | New agent or team file not imported |
| Every registered agent, team + workflow has a manifest entry | `app/main.py` ↔ `app/config.yaml` | Component added without description/prompts |
| Every env var in code is documented | code grep ↔ `AGENTS.md` env table + `example.env` | New var added without entries |
| Every var in `example.env` is read somewhere | `example.env` ↔ code grep | Stale var nobody reads |
| Every path mentioned in docs exists | `README.md`, `AGENTS.md`, `.agents/skills/*/SKILL.md` ↔ filesystem | Renamed or deleted file |
| Every script mentioned in docs is real + does what's claimed | docs ↔ `scripts/` | Renamed or behavior drifted |
| Architecture diagrams match registered agents + workflows | `README.md`, `AGENTS.md` Architecture sections | New agent or workflow missing from the tree |
| Eval cases reference real agents + tools | `evals/cases.py` ↔ `agents/`, `teams/` | Slug renamed or tool removed |
| Every workflow file is registered | [`workflows/`](../../../workflows/) ↔ `app/main.py` `workflows=[...]` | New workflow not imported/registered |
| Every schedule hits a real workflow | `app/schedules.py` `endpoint` ↔ workflow `id`s | Endpoint points at a renamed/removed workflow |
| The registry inventory in the docs matches the code | `app/registry.py` ↔ `AGENTS.md`'s registry paragraph + `README.md` | A block added or removed without the prose catching up |
| `Key Files` table in `AGENTS.md` matches reality | `AGENTS.md` ↔ filesystem | Renamed file, deleted file, new file not listed |
| Skill frontmatter + links resolve | `.agents/skills/*/SKILL.md` ↔ folder name + `../../../` link targets | name≠folder, broken `../../../` path, dead cross-skill link |
| `.claude/skills` symlink resolves | `.claude/skills` → `../.agents/skills` | Symlink missing or dangling |
| `.mcp.json` servers and the docs that reference them agree | `.mcp.json` ↔ docs + skills | URL changed, server renamed |
| MCP endpoint claims match code | `README.md`, `AGENTS.md`, `example.env` ↔ `app/main.py` `mcp_server` | `/mcp` promised in docs but flag flipped off, or JWT/auth wording drifted |
| `scripts/mcp_check.sh` calls a registered agent | `scripts/mcp_check.sh` hardcoded `agent_id` ↔ `app/main.py` `agents=[...]` | Agent renamed/removed; the MCP smoke check breaks or tests the wrong agent |

## 4. Live container smoke

First, confirm the live container is serving *this* repo's components — not a stale clone or a different worktree. The listing endpoints return two populations: code components registered in `app/main.py` (`is_component=false`) and components Platform Builder built at runtime (`is_component=true`). Only the first is this repo's, so compare on that filter:

```bash
curl -s http://localhost:8000/agents | jq -r '.[] | select(.is_component == false) | .id' | sort
curl -s http://localhost:8000/teams  | jq -r '.[] | select(.is_component == false) | .id' | sort
```

If *that* list doesn't match the slugs in `agents=[...]` / `teams=[...]`, stop and surface it to the user — the rest of Step 4 would be testing the wrong code. Common causes: the container was brought up from another worktree or clone of this repo (only one can bind localhost:8000), or `docker compose restart` is needed.

Then smoke each **code** component with one of its `quick_prompts` from `app/config.yaml` — every agent in `agents=[...]` **and** the team in `teams=[...]`. Agents use `/agents/<slug>/runs`; the team uses `/teams/agno/runs` with the same flags:

```bash
curl -sS -X POST http://localhost:8000/agents/<slug>/runs \
  -F "message=<one of the quick_prompts for this slug>" \
  -F "user_id=claude-review" \
  -F "stream=false" \
  -o /tmp/review-<slug>.json \
  -w "HTTP %{http_code} in %{time_total}s\n"

jq -r '.content // .' < /tmp/review-<slug>.json | head -20
```

Workflows stay out of the live smoke: `deployment-check` already runs on its daily cron, and `run-evals` spends real model budget. Step 3 — registered, schedules pointing at real ids — is their coverage.

Two components need more than a manifest prompt:

- **`platform-builder` — use its first quick prompt only.** "What can you build for me?" is plan-only. The other two are "Build …" asks, and the builder passes `publish=true` to finish a build, so smoking with one would create and publish a real, dispatchable component and leave it live. If a create fires anyway, `delete_new_builder_state(pre)` removes it — so take `pre = snapshot_builder_state()` before the builder's call (both from [`evals/hooks.py`](../../../evals/hooks.py); they sweep new components, schedules, learning rows, and notes). Nest that inside the learning bracket below rather than instead of it — the outer bracket is uncapped, whereas the builder helper refuses past 25 rows.
- **`agno` — capture is ungated.** Its quick prompts are read-only questions, but the model decides for itself what to file on any run: per-user profile and memory on all four components, plus notes and entities — shared by everyone on the platform — on the team. Bracket the whole smoke step, once around all the components rather than per prompt, with the `snapshot_learning_state` / `delete_new_learning_state` pair from [`evals/hooks.py`](../../../evals/hooks.py) — the full snippet is in [improve-agent Step 2](../improve-agent/SKILL.md).

  The diff works on row identity: it removes what the sweep created, cannot undo an edit *inside* a row that already existed, and sweeps a note a teammate files while you run. On a platform people are actively using, run Step 4 in a window you own, or tell the user you are skipping the delete and leaving whatever the smoke filed in place.

Pass = HTTP 200, non-empty content, no errors in the container logs:

```bash
docker logs agentos-api --since 30s 2>&1 | grep -E "Running: \w+\(" | head -40
```

(`Running: <tool>(` is agno's tool-call log line under `AGNO_DEBUG=True`, which compose sets for dev. Without it expect no matches — `HTTP 200` and a non-empty body are then your only signal.)

Then smoke the MCP interface (`mcp_server=True` in `app/main.py`):

```bash
./scripts/mcp_check.sh
```

Pass = `MCP OK — <n> tools` plus a non-empty agent response. It runs inside the container and calls `platform-manager` (read-only), so it is safe to run repeatedly.

Quality issues (response is plausible but wrong, missing citations, wrong tool fired) are out of scope — note them and recommend [`improve-agent`](../improve-agent/SKILL.md) (autonomous) or [`extend-agent`](../extend-agent/SKILL.md) (user-driven) depending on whether the user has a specific fix in mind.

## 5. Format + validate

```bash
source .venv/bin/activate  # if not already active
./scripts/format.sh
./scripts/validate.sh
```

`format.sh` auto-fixes. `validate.sh` gates on formatting as well as lint and types, so keep that order — a sweep that skips `format.sh` fails validate on its own edits. If validate fails, surface the errors verbatim; don't suppress them.

## 6. Evals (ask before running)

The release tag hits OpenAI, so ask first:

> Run `python -m evals --tag release` to confirm no agent regressed? (Hits OpenAI; takes 1-3 minutes.)

If any case fails, add it to "Needs your call" with [`eval-and-improve`](../eval-and-improve/SKILL.md) as the recommended follow-up. If the user declines, skip this step.

## 7. Report

If nothing was fixed and nothing flagged, skip the first two blocks below and just print: *"Repo is consistent and the live container is healthy. No follow-up needed."* No commit suggested.

Otherwise, wrap up with three blocks, in order:

**Fixed automatically** — one line per change, with file path. Terse.

**Needs your call** — flagged items, ranked by severity. For each: one-line description, file (and line if useful), recommended action.

**Diff + next step**:

```bash
git diff --stat
```

- Suggested commit message — `chore: review-and-improve sweep` plus one short bullet per fix bucket.
- Recommended follow-up — usually [`improve-agent`](../improve-agent/SKILL.md) (if a live agent looked off) or [`eval-and-improve`](../eval-and-improve/SKILL.md) (if evals failed).
