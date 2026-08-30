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

In the same message, below the connect direction, say let's build your first agent, and ask the one question that starts it — plain text, no structured choice control here even though create-agent's own instructions offer one (the override is for this kickoff message only):

> Now let's build your first agent. Do you have a product you'd like to build an agent for — or a product you use that you'd like an agent for? Give me its docs or website URL and I'll build an agent that answers questions about it from its own docs, ready to serve in your product, in claude.ai and ChatGPT, and over MCP.
>
> Or if you have something else in mind — issue triage, release notes, your weekly update — say it in your own words and I'll build that instead.

Whatever they type is their first discovery answer for [`create-agent`](../create-agent/SKILL.md): a URL or product name takes the **product-agent pattern** in that skill's Step 3 (ingest, knowledge-only agent, three-probe smoke); anything else takes its normal path. The message closes with the first build move — never with "ready?" or "connected yet?".

### The product-agent brief

What you hand create-agent when they name a product — a spec for you, never pasted to the user. It's complete, so that skill builds immediately without asking anything more:

- Product-agent pattern from create-agent Step 3: dedicated base `"<Product> Knowledge"`, sitemap discovery (follow a sitemap index), page cap 50, one content row per page.
- Ingestion route by what's in `.env`: `PARALLEL_API_KEY` set → Parallel Extract (citations work); only `OPENAI_API_KEY` → the WebsiteReader fallback, and tell them citations need the Parallel key — a fresh clone usually lands here, and the agent still works.
- Knowledge search as the only tool, no `learning=`, the instruction template as written — the "What counts as documented" rules are what keep it from answering from memory.
- Three smoke probes: a covered question, a likely-uncovered one, an off-topic one.

Then follow the skill through its smoke test: ingest, generate the agent, register it (agent *and* base), and prove it live. Show the user their agent's first answer, then land where it now lives — say all of it in the same breath as the answer:

- **In the UI they just connected** — a **Refresh** puts their agent in the Agents list next to the built-in ones, and its base on the Knowledge page.
- **On Agno's roster.** Registering the agent in `app/main.py` is also what puts it in front of the team lead: Agno discovers every component this platform registers and can run it by name, so "Agno, ask the <Product> agent…" now works — from the AgentOS UI, from Slack, from any MCP client. Their agent joined the platform, not just the repo.
- **Ready to serve** — over REST inside their product and over MCP right now; from claude.ai and ChatGPT once deployed (Step 8 names the deploy).

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
