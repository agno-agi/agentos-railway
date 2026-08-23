---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, boot the containers, prove the MCP endpoint live, connect the AgentOS UI, then build the user's first agent. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/setup-platform`) or describe the task and it triggers automatically._

You are taking the user from a fresh clone to a running platform with their first agent live on it. The wow moment is Step 6. Everything before it is setup; everything after it is handing over the loop. Pace accordingly.

**Be self-driving:** anything you can do — open a file, open a URL, launch an app — do it. Stop when progress needs a human: typing a secret, installing software, a sign-in the flow can't continue without. When you do stop, tell the user exactly what to do. Never print or echo secret values.

**Narrate the trip:** open with a quick map of what's about to happen, shaped like this — tune the words, keep the shape — then a line as each step starts and a word when it lands. Light touch: a sentence or two per step. The map's numbers are this skill's step numbers; Step 0 is your own prep and never appears in it.

```text
Kicking off /setup-platform. Here's the map for this trip:

1. Docker — confirm it's installed and running
2. Environment — .env and your OpenAI key
3. Boot — build and start the platform containers
4. Prove it — a real agent answer over the MCP endpoint
5. Connect the UI — os.agno.com, one click
6. First agent — we build it together, live
7. Make it yours — your platform in its own private repo
8. The loop — the skills you own from here
```

## 0. Read the manual

Read [`AGENTS.md`](../../../AGENTS.md) end to end — it's the source of truth for how this platform works and answers most questions you'll hit along the way.

## 1. Docker

Confirm Docker is installed and running (`docker info` succeeds). If it's installed but not running, start it (`open -a Docker` on macOS) and poll until it's up. Stop for the user only if Docker isn't installed — give them the steps to install Docker Desktop and wait.

## 2. Environment

Run `cp example.env .env`, then help the user set their `OPENAI_API_KEY`:

- If it's already set in their shell, say you found one and offer to copy it in — move the value across without reading or printing it.
- Otherwise open `.env` in their editor (cursor, code, etc.) and ask them to paste the key in. Never open a terminal editor like vim or nano from your own shell — it will hang the session.

## 3. Boot

Start the platform with `docker compose up -d --build`, then poll http://localhost:8000/docs until it returns 200 (the first build takes a few minutes). If it never comes up, read `docker compose logs agentos-api` and fix what you find.

## 4. Prove it

Run `./scripts/mcp_check.sh` — it should print "MCP OK" and a real agent answer. Quote that answer to the user — it's their platform manager talking. And let them know the platform's MCP server is live.

## 5. Connect the AgentOS UI

The UI is where they chat with their agents and inspect sessions, memory, and evals. Open with the news that the platform is up and it's time to connect to it on os.agno.com, then render the connection details as a table, something like this:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com |
| Connection type | **Local** |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` (the default) |

Follow the table with one line of direction. Most users arrive from the Agno onboarding with the **Connect your OS** screen still open, showing "Awaiting connection": tell them to flip back to that tab and hit **Connect OS** (the form already matches the table). If they don't have it open: https://os.agno.com, sign in, **Connect OS**, fill the form from the table.

Don't gate on the click, and never ask whether they'd rather connect or build first: after the connect direction, bridge with "now let's build your first agent" and deliver Step 6's build move. If they'd rather skip the UI, carry on — they can connect anytime.

This table is a hard checkpoint: it gets written before anything from Step 6 happens.

## 6. Build their first agent

In the same message, below the connect direction, say let's build your first agent (they can always run `/create-agent` later for more), and start [`create-agent`](../create-agent/SKILL.md): if they've hinted at an idea anywhere in the session, propose that; otherwise offer **one** recommendation, carrying that skill's discovery question as its fallback. Keep it plain text — no structured choice control here, even though create-agent's own instructions offer one. (The override is for this kickoff message only — once they answer, that skill's guidance applies as written.) The recommendation goes in the message like this:

> Here's the one I'd build for you: **Radar**: a quick brief on what the AI labs and agent frameworks shipped. Five items max, one line each, every one with a link, no hype. It keeps a ledger of what it's already sent you, so every brief is only what's new — and it learns what you care about, so "stop showing me funding rounds" sticks.
>
> Or something from your own week instead — issue triage, release notes, your weekly update. Say it in your own words and I'll build that.

The recommendation is calibration, not a menu — whatever they type is their first discovery answer, and create-agent's follow-up dig still applies when the answer leaves the design open (a complete brief builds immediately, per that skill). The message closes with the first build move — never with "ready?" or "connected yet?".

### The Radar brief

If they take it, this is what you hand create-agent — a spec for you, never pasted to the user. It's a complete brief, so that skill builds immediately without asking anything.

- **Radar** (`radar`), direct-tools pattern, searching through the **keyless Parallel MCP** — the one search route that works on a fresh clone carrying only `OPENAI_API_KEY` (the wiring snippet and the `ddgs` import trap are in create-agent Step 2). Searches the web for what the major AI labs and agent frameworks released or announced.
- Max 5 items, one line each, every item with a source link. No hype adjectives — what happened, not how exciting it is.
- **The delta comes from a ledger, not a clock.** `check_lines` says which URLs are already recorded, `append_file(unique=True)` records the new ones. Whatever isn't in the ledger is the brief. No schedule, no `last_run` timestamp.
- Nothing new is one line that says since when ("nothing new since Tuesday"). Never pad the brief.
- **Two answer modes.** "What's new?" → the delta-filtered brief. "What's going on with X?" → answer it from search, no suppression; recording happens either way. The ledger filters the brief, never a direct question.
- Preferences live in a file it reads every run, so a standing rule binds on any run from any surface.

Two things the code has to get right:

- **No `learning=` on this one, and the reason goes in a comment.** Its state is the platform's, not any one person's: profile and memory rows are keyed by user id alone, and in agentic mode their tools are not registered at all on a run that carries no user id, so a brief triggered by a schedule would write to nothing and read back nothing.
- **Its files live in the shared notebook, under `radar/`.** That is the platform's one file store ([`app/notes.py`](../../../app/notes.py)): the ledger at `radar/reported.md` (one canonical URL per line, nothing else — `check_lines` is whole-line exact match), each brief at `radar/briefs/<date>.md` (so "nothing new since Tuesday" is a `list_files` over that directory), preferences at `radar/preferences.md`. Filing there is what lets "Agno, what did radar find this week?" work — Agno reads the same notebook.

Wire it with the shared notebook's scoped tools alongside the web tools (create-agent Step 2 has the `MCPTools` snippet):

```python
from app.notes import get_shared_notes_tools

radar = Agent(
    ...
    tools=[*get_shared_notes_tools(), web_tools],
    instructions=INSTRUCTIONS,
)
```

`get_shared_notes_tools()` carries its own usage instructions, so nothing is appended to `INSTRUCTIONS` for it. The MCP exposes `web_search` and `web_fetch` — that is the whole search surface, so Radar's own `INSTRUCTIONS` name those two rather than a generic "search the web", and name its three paths under `radar/`.

Then follow the skill through its smoke test: work out what to build, generate the agent, register it, and prove it live. Show the user their agent's first answer, then land the two places it now lives — say both in the same breath as the answer:

- **In the UI they just connected** — a **Refresh** puts their agent in the Agents list next to the built-in ones.
- **On Agno's roster.** Registering the agent in `app/main.py` is also what puts it in front of the team lead: Agno discovers every component this platform registers and can run it by name, so "Agno, have radar scan the week" now works — from the AgentOS UI, from Slack, from any MCP client. Their agent joined the platform, not just the repo.

Then come back here: stop before that skill's own closing and let Steps 7 and 8 replace it, so the handover lands once.

If they push back or want to stop, that's fine — carry on and adapt the remaining steps.

## 7. Make it yours

Their clone's `origin` still points at the public template — a repo they can't push to. Offer to give it a home of its own; a quick beat, not a gate:

```sh
git remote rename origin upstream    # the template stays connected for updates
git remote add origin <their-private-repo-url>
git push -u origin main
```

If `gh` is installed and signed in, drive it end to end — after the rename, `gh repo create agent-platform --private --source=. --push` creates the private repo, wires it in as `origin`, and pushes. Otherwise point them at https://github.com/new (private is the right default), then run the add and push once they paste the URL. Either way `upstream` keeps template updates a `git pull upstream main` away. If they'd rather skip it, carry on — nothing later depends on it.

## 8. Hand over the loop

Finish with a short summary of what you built together and the loop the user now owns — leading with whichever loop the smoke test suggested:

- [`/extend-agent`](../extend-agent/SKILL.md) — change the agent: add a tool or source, add a capability, fix a known bug.
- [`/improve-agent`](../improve-agent/SKILL.md) — recursively improve it using simulations and probes.
- [`/create-agent`](../create-agent/SKILL.md) — whenever they want another.

Mention in one line that they can also connect the platform to coding agents (like yourself) with `uvx agno connect`, and to claude.ai / ChatGPT over OAuth once the platform is deployed with a public URL — [`/deploy-platform`](../deploy-platform/SKILL.md) runs that deploy when they're ready.

One more line, and only if the trip has gone smoothly enough to carry it: two shared surfaces ship empty and are theirs to fill. The **Knowledge** page in the UI takes documents — drop a handbook or a spec in and any agent can be wired to answer from it. The **shared notebook** is where Agno files what the team tells it, and where a built agent files what it finds, so the platform accumulates rather than restarting each session.
