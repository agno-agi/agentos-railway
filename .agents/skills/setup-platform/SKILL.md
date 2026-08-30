---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, boot the containers, prove the MCP endpoint live, connect the AgentOS UI, then build the user's first agent. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _Coding-agent workflow: run as `/setup-platform` or by describing the task._

Take the user from a fresh clone to a running platform with their first agent live on it. Step 6 is the point of the trip; everything before it is setup, everything after is hand-over.

**Be self-driving:** do anything you can do yourself (open a file, open a URL, launch an app). Stop only for what needs a human: a secret, an install, a sign-in. Never print or echo secret values.

**Narrate:** open with this map (tune the words, keep the shape), then a line per step.

```text
Kicking off /setup-platform. Here's the map:

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

Read [`AGENTS.md`](../../../AGENTS.md) end to end.

## 1. Docker

`docker info` must succeed. Installed but not running → start it (`open -a Docker` on macOS) and poll. Not installed → stop and give install steps.

## 2. Environment

`cp example.env .env`, then set `OPENAI_API_KEY`:

- Already in their shell → say so and copy it across without reading or printing it.
- Otherwise open `.env` in their editor (`cursor`, `code`) and ask them to paste it. Never open a terminal editor from your shell — it hangs the session.

## 3. Boot

`docker compose up -d --build`, then poll http://localhost:8000/docs until 200 (first build takes minutes). If it never comes up, read `docker compose logs agentos-api`.

## 4. Prove it

`./scripts/mcp_check.sh` prints "MCP OK" and a real agent answer. Quote the answer — it's their Platform Manager — and say the MCP server is live.

## 5. Connect the AgentOS UI

Render the connection as a table, then one line of direction:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com |
| Connection type | **Local** |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` |

Most users arrive from the Agno onboarding with **Connect your OS** still open ("Awaiting connection"): tell them to flip back and hit **Connect OS**. Otherwise: sign in, **Connect OS**, fill the form from the table.

Don't gate on the click and don't ask "connect or build first?" — bridge straight into Step 6 in the same message. This table is written before anything from Step 6.

## 6. Build their first agent

Below the connect direction, ask the one question that starts it — plain text, no structured choice control:

> Now let's build your first agent. Do you have a product you'd like to build an agent for — or a product you use that you'd like an agent for? Give me its docs or website URL and I'll build an agent that answers questions about it from its own docs, ready to serve in your product, in claude.ai and ChatGPT, and over MCP.
>
> Or if you have something else in mind — issue triage, release notes, your weekly update — say it in your own words and I'll build that instead.

Whatever they type is the first discovery answer for [`create-agent`](../create-agent/SKILL.md): a URL or product name takes its **product-agent pattern** (Step 3 there); anything else takes its normal path. Close the message with the first build move, never with "ready?".

**The product brief** you hand create-agent when they name a product — complete, so it builds without asking more: the product pattern (Step 3 there), ingest with `app/tools.py`'s `ingest_url` inside the container (Parallel-backed when `PARALLEL_API_KEY` is set, the built-in fetcher otherwise — same rows and citations either way), page cap 50, `knowledge=product_knowledge`, `learning=shared_learning`, instructions you write that carry the grounding rules in create-agent's product pattern, no other tools; three smoke probes.

Follow create-agent through its smoke test, then land where the agent now lives, in the same breath as its first answer:

- **In the UI** — **Refresh** puts it in the Agents list, and its base on the Knowledge page.
- **On Agno's roster** — registering in `app/main.py` lets Agno run it by name ("Agno, ask the <Product> agent…") from the UI, Slack, or any MCP client.
- **Ready to serve** — REST inside their product and MCP now; claude.ai and ChatGPT once deployed (Step 8).

Stop before create-agent's own closing — Steps 7 and 8 replace it. If they push back or want to stop, adapt and carry on.

## 7. Make it yours

`origin` still points at the public template. Offer a home of its own — a quick beat, not a gate:

```sh
git remote rename origin upstream    # the template stays connected for updates
git remote add origin <their-private-repo-url>
git push -u origin main
```

With `gh` signed in: `gh repo create agent-platform --private --source=. --push` after the rename. Otherwise point them at https://github.com/new (private) and run the add and push once they paste the URL. `git pull upstream main` brings template updates.

## 8. Hand over the loop

Short summary of what you built, then the loop they own — lead with whichever the smoke test suggested:

- [`/extend-agent`](../extend-agent/SKILL.md) — change the agent: a tool, a capability, a known bug.
- [`/improve-agent`](../improve-agent/SKILL.md) — harden it autonomously with probes.
- [`/create-agent`](../create-agent/SKILL.md) — another agent.

One line: coding agents connect with `uvx agno connect`; claude.ai / ChatGPT connect over OAuth once deployed — [`/deploy-platform`](../deploy-platform/SKILL.md) does that.

If the trip went smoothly, one more: the **Knowledge** page and the **shared notebook** ship empty and are theirs to fill.
