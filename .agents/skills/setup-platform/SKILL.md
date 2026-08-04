---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, boot the containers, prove the MCP endpoint live, connect the AgentOS UI, then build the user's first agent. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/setup-platform`) or describe the task and it triggers automatically._

You are taking the user from a fresh clone to a running platform with their first agent live on it. The wow moment is Step 7 — watching their own agent get built and answer, minutes after cloning, then appear in the UI they connected moments earlier. Everything before it is setup; everything after it is handing over the loop. Pace accordingly.

**Be self-driving:** anything you can do — open a file, open a URL, launch an app — do it. Stop when progress needs a human: typing a secret, installing software, a sign-in the flow can't continue without. When you do stop, tell the user exactly what to do. Never print or echo secret values.

**Narrate the trip:** open with a quick map of what's about to happen, shaped like this — tune the words, keep the shape — then a line as each step starts and a word when it lands. Light touch: a sentence or two per step, so the user always knows where they are and what's left.

```text
Kicking off /setup-platform. Here's the map for this trip:

1. Docker — confirm it's installed and running
2. Environment — .env and your OpenAI key
3. Boot — build and start the platform containers
4. Prove it — a real agent answer over the MCP endpoint
5. Connect the UI — os.agno.com, one click
6. First agent — we build it together, live
7. Make it yours — your platform in its own private repo
```

## 1. Read the manual

Read [`AGENTS.md`](../../../AGENTS.md) end to end — it's the source of truth for how this platform works and answers most questions you'll hit along the way.

## 2. Docker

Confirm Docker is installed and running (`docker info` succeeds). If it's installed but not running, start it (`open -a Docker` on macOS) and poll until it's up. Stop for the user only if Docker isn't installed — give them the steps to install Docker Desktop and wait.

## 3. Environment

Run `cp example.env .env`, then help the user set their `OPENAI_API_KEY`:

- If it's already set in their shell, say you found one and offer to copy it in — move the value across without reading or printing it.
- Otherwise open `.env` in their editor (cursor, code, etc.) and ask them to paste the key in. Never open a terminal editor like vim or nano from your own shell — it will hang the session.

## 4. Boot

Start the platform with `docker compose up -d --build`, then poll http://localhost:8000/docs until it returns 200 (the first build takes a few minutes). If it never comes up, read `docker compose logs agentos-api` and fix what you find.

## 5. Prove it

Run `./scripts/mcp_check.sh` — it should print "MCP OK" and a real agent answer. Quote that answer to the user — it's their platform manager talking. And let them know the platform's MCP server is live.

## 6. Connect the AgentOS UI

Their platform is live — show them how to connect to the AgentOS UI so their first agent lands somewhere they can watch. The UI is where they chat with their agents and inspect sessions, memory, and evals. Open with the news that the platform is up and it's time to connect to it on os.agno.com, then render the connection details as a table, something like this:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com |
| Connection type | **Local** |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` (the default) |

Follow the table with one line of direction. Most users arrive from the Agno onboarding with the **Connect your OS** screen still open, showing "Awaiting connection": tell them to flip back to that tab and hit **Connect OS** (the form already matches the table). If they don't have it open: https://os.agno.com, sign in, **Connect OS**, fill the form from the table.

Don't gate on the click, and never ask whether they'd rather connect or build first — the table has already told them exactly what to do, so the same message rolls straight on: after the connect direction, bridge with "now let's build your first agent" and deliver Step 7's build move. The platform connects while you're already talking about what to build; if they'd rather skip the UI, carry on — they can connect anytime.

This table is a hard checkpoint: it gets written before anything from Step 7 happens. Skipping it to get to the first-agent question is a failure mode for this skill.

## 7. Build their first agent

Now the fun part — roll straight in. In the same message, directly below the connection table and its one line of direction, say let's build your first agent (they can always run `/create-agent` later for more), and start [`create-agent`](../create-agent/SKILL.md): if they've hinted at an idea anywhere in the session, propose that; otherwise offer **one** recommendation, carrying that skill's discovery question as its fallback — a brand-new user needs somewhere to start, and one concrete idea is easier to answer than a menu. Keep it plain text — no structured choice control here, even though create-agent's own instructions offer one: a tool-call picker breaks the flow of the message, and typing a few words is easier than picking. (The override is for this kickoff message only — once they answer, that skill's guidance applies as written.) The recommendation goes in the message like this:

> Here's the one I'd build for you: **Radar**: a quick brief on what the AI labs and agent frameworks shipped. Five items max, one line each, every one with a link, no hype. It keeps a ledger of what it's already sent you, so every brief is only what's new — and it learns what you care about, so "stop showing me funding rounds" sticks.
>
> Or something from your own week instead — issue triage, release notes, your weekly update. Say it in your own words and I'll build that.

The recommendation is calibration, not a menu — whatever they type is their first discovery answer, create-agent's follow-up dig still applies when the answer leaves the design open (a complete brief builds immediately, per that skill), and their own words always beat Radar. Your live-and-connect message runs platform-up (MCP answer quoted) → connection table → connect direction → build kickoff, and closes with the first build move — the recommendation, or your build proposal if they've already hinted at an idea — never with "ready?" or "connected yet?".

### The Radar brief

If they take it, this is what you hand create-agent — a spec for you, never pasted to the user. It's a complete brief, so that skill builds immediately without asking anything.

- **Radar** (`radar`), direct-tools pattern, keyless `WebSearchTools` so a fresh clone with only `OPENAI_API_KEY` builds on the first try. Searches the web for what the major AI labs and agent frameworks released or announced.
- Max 5 items, one line each, every item with a source link. No hype adjectives — what happened, not how exciting it is.
- **The delta comes from a ledger, not a clock.** Two plain functions over an agent `FileSystem`: one checks whether items were already reported, one records them. Whatever isn't in the ledger is the brief. No schedule, no `last_run` timestamp.
- Nothing new is one line that says since when ("nothing new since Tuesday"). Never pad the brief.
- **Two answer modes.** "What's new?" → the delta-filtered brief. "What's going on with X?" → answer it from search, no suppression; recording happens either way. The ledger filters the brief, never a direct question — otherwise a real question gets a "nothing new" that is technically true and useless.
- Preferences live in a file it reads every run, so a standing rule binds on any run from any surface, and the user can open and edit it.

Three things the code has to get right:

- **`enable_agentic_memory=False`** — against the default in create-agent's required structure, with the reason in a comment. Radar's state has to be readable by runs that carry no user id, and the ledger needs exact membership rather than semantic recall; agentic memory would also become a second home for preferences that already live in the file.
- **The ledger gets its own directory, and its lines are bare keys.** `contains()` is whole-line exact match scoped to a directory, not a file — so `reported/log.md` holds one canonical URL per line and nothing else. A title or date on that line breaks the match, and sharing a directory with the preferences file makes membership checks collide with unrelated lines.
- **Each brief is filed as its own note** (`briefs/<date>.md`). That's where "nothing new since Tuesday" comes from — `list()` over that directory — and it gives "show me last week's briefs" for free, without the delta ever depending on a timestamp.

Wire it the way [`agents/chief.py`](../../../agents/chief.py) does: `FileSystem(get_postgres_db(), namespace="radar")`, then `tools=[fs.tools(), WebSearchTools(), was_reported, record_reported]`. The file tools are what let it manage the preferences file and the brief notes; the instructions say the ledger is only ever touched through the two functions.

Then follow the skill through its smoke test: work out what to build, generate the agent, register it, and prove it live. Show the user their agent's first answer — and tell them that if they connected the UI, a **Refresh** puts their agent in the Agents list next to the built-in ones. Then come back here: stop before that skill's own closing and let Steps 8 and 9 replace it, so the handover lands once.

If they push back or want to stop, that's fine — carry on and adapt the remaining steps.

## 8. Make it yours

Their clone's `origin` still points at the public template — a repo they can't push to — so the platform they just built has no home of its own. Offer to give it one; a quick beat, not a gate:

```sh
git remote rename origin upstream    # the template stays connected for updates
git remote add origin <their-private-repo-url>
git push -u origin main
```

If `gh` is installed and signed in, drive it end to end — after the rename, `gh repo create agent-platform --private --source=. --push` creates the private repo, wires it in as `origin`, and pushes. Otherwise point them at https://github.com/new (private is the right default), then run the add and push once they paste the URL. Either way `upstream` keeps template updates a `git pull upstream main` away. If they'd rather skip it, carry on — nothing later depends on it.

## 9. Hand over the loop

Finish with a short summary of what you built together and the loop the user now owns — leading with whichever loop the smoke test suggested:

- [`/extend-agent`](../extend-agent/SKILL.md) — change the agent: add a tool or source, add a capability, fix a known bug.
- [`/improve-agent`](../improve-agent/SKILL.md) — recursively improve it using simulations and probes.
- [`/create-agent`](../create-agent/SKILL.md) — whenever they want another.

Mention in one line that they can also connect the platform to coding agents (like yourself) with `uvx agno connect`, and to claude.ai / ChatGPT over OAuth once the platform is deployed with a public URL — [`/deploy-platform`](../deploy-platform/SKILL.md) runs that deploy when they're ready.
