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
4. Prove it — MCP handshake and tools; an optional agent answer
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

If `.env` does not exist, `cp example.env .env`, then set `OPENAI_API_KEY`:

- Already in their shell → copy the credentials across without displaying or logging their values.
- Otherwise open `.env` in their editor (`cursor`, `code`) and ask them to paste it. Never open a terminal editor from your shell — it hangs the session.

Coding agents are opt-in; see [harness setup](../../../docs/harnesses.md).
If enabled, Claude Engineer needs its own credentials. If the user chooses Claude Code OAuth, remove
the `ANTHROPIC_API_KEY` placeholder and set `CLAUDE_CODE_OAUTH_TOKEN` instead. The API
container does not inherit a host Claude login. If Claude credentials are unavailable,
report that Claude Engineer cannot run; do not present API startup as verification of it.

## 3. Boot

For standard development, `docker compose up -d --build`, then poll http://localhost:8000/docs until 200 (first build takes minutes). If it never comes up, read `docker compose logs agentos-api`.

For sandbox development, follow the [sandbox setup guide](../../../docs/harnesses.md#local-docker-sandbox).
Set `SANDBOX_ENABLED = True` and `REPOSITORY` in `app/sandbox.py`, build the sandbox
image, and use the same Compose API. Compose selects `SANDBOX_PROVIDER=docker` and
mounts the daemon socket into the API only; do not mount it into coding sandboxes.
The pinned framework admits sandbox HTTP runs through the durable PostgreSQL queue.
Configuration and API startup do not prove execution: verify a coding agent HTTP run and
Company Task acceptance/completion separately. Keep the Product repository Source aligned
with `REPOSITORY.url`; never bypass a framework rejection.

## 4. Prove it

`./scripts/mcp_check.sh` initializes MCP and verifies the required tools without a model call. For an answer, use `--prompt "<read-only prompt>"`; that spends model calls. Report which check was actually run.

## 5. Connect the AgentOS UI

Render the connection as a table, then one line of direction:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com/?ref=railway-template |
| Connection type | **Local** |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` |

Most users arrive from the Agno onboarding with **Connect your OS** still open ("Awaiting connection"): tell them to flip back and hit **Connect OS**. Otherwise: sign in, **Connect OS**, fill the form from the table.

Don't gate on the click and don't ask "connect or build first?" — bridge straight into Step 6 in the same message. This table is written before anything from Step 6.

## 6. Build their first agent

If the user already described the agent they want, pass that request directly to
[`create-agent`](../create-agent/SKILL.md). Otherwise, below the connect direction,
ask one plain-text question and wait for the answer:

> What would you like your first agent to do?

Use their answer as create-agent's discovery input and follow that skill immediately.
Do not ask them to invoke it separately or repeat a brief they already supplied.
A product name or URL is context; it does not by itself request a documentation Q&A agent.

Follow create-agent through its smoke test, then land where the agent now lives, in the same breath as its first answer:

- **In the UI** — **Refresh** puts it in the Agents list. Show its knowledge base only if one was created.
- **On OS Manager's roster** — registering in `app/main.py` lets OS Manager run it by name ("OS Manager, ask the <agent name>…" through the `os_manager` MCP tool) from the UI or an MCP client; Slack when configured.
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
- [`/improve`](../improve/SKILL.md) — harden the agent through simulations, diagnosis and verified fixes; optionally turn useful scenarios into evals.
- [`/create-agent`](../create-agent/SKILL.md) — another agent.

One line: coding agents connect with `uvx agno connect`; claude.ai / ChatGPT connect over OAuth once deployed — [`/deploy-platform`](../deploy-platform/SKILL.md) does that.

If the trip went smoothly, one more: the **Knowledge** page and the **shared notebook** ship empty and are theirs to fill.
