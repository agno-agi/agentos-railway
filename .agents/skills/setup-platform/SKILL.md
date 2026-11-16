---
name: setup-platform
description: Set up this AgentOS from a fresh clone — confirm Docker, configure .env, start the containers, check the MCP endpoint, connect the AgentOS UI, then build the user's first agent. Use when the user asks to set up the platform, get started, or bring this repo up on a new machine.
---

# Set Up the Platform

> _Coding-agent workflow: run as `/setup-platform` or by describing the task._

Take the user from a fresh clone to a running platform with their first agent on it. Do
everything you can yourself and stop only for what needs a person: a secret, an install or a
sign-in. Never print secret values. Read [`AGENTS.md`](../../../AGENTS.md) first.

## 1. Start the platform

1. `docker info` must succeed. Start Docker if it is installed; give install steps if it is not.
2. If `.env` is missing, `cp example.env .env`. Set `OPENAI_API_KEY`: copy it from the user's
   shell without displaying it, or open `.env` in their editor (`code`, `cursor`) and ask them
   to paste it. Do not open a terminal editor from your shell; it hangs the session.
   After changing `.env` on a running stack, run `docker compose up -d agentos-api`.
3. `docker compose up -d --build`, then wait for `http://localhost:8000/docs` to return 200.
   The first build takes a few minutes. If it does not come up, read
   `docker compose logs agentos-api`.
4. `./scripts/mcp_check.sh` confirms the MCP endpoint and its tools without a model call.

## 2. Connect the AgentOS UI

Give the user this table:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com/?ref=railway-template |
| Connection type | **Local** |
| Endpoint | `http://localhost:8000` |
| Name | `Local AgentOS` |

If they came from Agno onboarding, **Connect OS** is already open. Otherwise they sign in and
choose **Connect OS**. Suggest they open Super Agent and tell it what their company does.
Do not wait for the click; go on to the first agent.

## 3. Build their first agent

Ask "What would you like your first agent to do?" unless they already said. Then follow
[`create-agent`](../create-agent/SKILL.md) with their answer.

## 4. Make it theirs

`origin` still points at the public template. Offer to move the work to their own private
repository:

```sh
git remote rename origin upstream    # the template stays connected for updates
git remote add origin <their-private-repo-url>
git push -u origin main
```

With `gh` signed in, `gh repo create <name> --private --source=. --push` replaces the last two
commands. `git pull upstream main` brings template updates later.

## 5. Hand over

Say what is running and what you verified. Then point to what comes next:

- [`/extend-agent`](../extend-agent/SKILL.md) to change an agent.
- [`/improve`](../improve/SKILL.md) to harden one.
- [`/deploy-platform`](../deploy-platform/SKILL.md) to put the platform in production.
- Claude and Codex coding agents are off by default; [docs/harnesses.md](../../../docs/harnesses.md)
  turns them on.
