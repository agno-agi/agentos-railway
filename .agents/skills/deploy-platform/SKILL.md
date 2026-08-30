---
name: deploy-platform
description: Deploy this AgentOS to production with this template's deploy scripts — preflight the provider CLI and account, run the up.sh script, complete the JWT key step, verify the live platform on its public URL, then hand over the redeploy/logs/teardown instructions. Use this skill when the user asks to deploy, ship to production, go live, or take the platform to prod.
---

# Deploy the Platform

> _Coding-agent workflow: run as `/deploy-platform` or by describing the task._

Take the locally-proven platform to a live public URL. This creates real, billed cloud resources — say so before creating anything, and name the teardown script in the same breath.

**Be self-driving:** run every script and check yourself. Stop only for a provider login, a browser-only step, or a key only the user can mint — and tell them to run interactive commands in a separate terminal (CLI logins need a TTY and a browser). Never print secret values; the two exceptions are the JWT verification key (public) and the `MCP_CONNECT_SECRET` the up script prints itself.

**Narrate:** open with this map plus the cost sentence, then a line per step. On a redeploy (Step 3 finds the platform live) the map is three beats — push, prove, hand back — and the cost sentence is already spent.

```text
Kicking off /deploy-platform. Here's the map:

1. Read the deploy layer — scripts + README, pick the mode
2. Preflight — provider CLI + login, cost and exit, production env
3. Deploy — the up script (compute + Postgres + public domain)
4. JWT key — connect os.agno.com Live, land the public key, sync it
5. Prove it live — logs, /docs 200, /mcp 401 challenge, UI Connect
6. Hand over — redeploy, logs, teardown, chat + coding-agent connect

This creates real, billed resources on your account. The exit is one
command away — the down script deletes everything (asks to confirm; --yes skips).
```

## 1. Read the deploy layer

Read [`AGENTS.md`](../../../AGENTS.md), the README's production section, and `scripts/<provider>/` — never invent a step. Pick the mode by who provisions the target: **Conduct** (the up script provisions compute and URL on a managed provider — the main path), **Conduct over owned infra** (same scripts onto the user's own cluster; add Step 7), or **Manual-guide** (no deploy scripts; walk the README's deploy section with Steps 4, 5, and 7).

## 2. Preflight

- **CLI + account:** the provider CLI is installed and authed (a `whoami`-style probe). Not logged in → hand over the login command for a separate terminal, re-probe when they say ready.
- **Cost + exit:** one sentence — billed resources, `down.sh` deletes everything.
- **Production env:** `.env.production` (`cp example.env .env.production` if missing) with a real `OPENAI_API_KEY` set the setup-platform way (editor paste, never read or print). `RUNTIME_ENV` must **not** be `dev` there — it syncs to the cloud and disables auth.
- **Unattended-run inputs:** for each provisioning call the up script makes, does it pin the account scope (workspace, org, project, region)? If the account has more than one and nothing pins it, the CLI opens a picker that fails or hangs — **stop before creating anything** and hand the user the pinning flag/env var or the one interactive init/link command. Never let it resolve by guess.

## 3. Deploy

**First or re-deploy?** Read `AGENTOS_URL` from the production env; if it names a domain, probe `<domain>/docs`. 200 → already live; the up script would provision a *second* project. Take the redeploy path: code → `redeploy.sh`; env/secret → `env-sync.sh` (both, in that order, if both changed); skip Step 4; run Steps 5–6. No answer → nothing is serving; continue as a first deploy.

Otherwise run the up script and narrate its phases. First creates can take twenty-plus minutes. If the README names a browser step, relay it first. When it finishes, read the live URL from `AGENTOS_URL` and keep the printed `MCP_CONNECT_SECRET` for Step 6. **A keyless first deploy refusing to start is by design** — auth is on and the app exits without a key; tell the user before they see it, then read the provider logs (bounded, never streaming) and confirm the startup error is the missing key.

## 4. The JWT key

Say plainly: deployed, not live yet — this key is the one piece only they can add, and the platform comes up the moment it lands. Render the table and the click path fresh in that message:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com |
| Connection type | **Live** |
| Endpoint | `https://<the AGENTOS_URL domain>` |
| Name | `Live AgentOS` |

1. **Connect OS** → **Live** → enter the endpoint → name it. (Live connections are a paid feature — `PLATFORM30` takes a month off.)
2. Flip **Token-Based Authorization (JWT)** on — on the connect panel — then **Connect**. Copy the public key the UI generates.
3. Already connected or can't find the toggle? **Settings → OS & Security → Token-Based Authorization (JWT)**.

These clicks are canonical; if the up script's copy differs, relay these and note the drift. Offer both hand-offs: paste the key here (it's public) and you write it into `.env.production`, or they paste it on the `JWT_VERIFICATION_KEY=` line. The PEM must land quoted, multi-line. Then `env-sync.sh` applies it.

Name the alternative once, clearly not recommended: `authorization=False` in `app/main.py` makes the platform public; the scripts refuse `RUNTIME_ENV=dev` unless `ALLOW_UNAUTHENTICATED_DEPLOY=1`.

## 5. Prove it live

Every probe against the public domain, never localhost:

- Provider logs (bounded): clean boot, schedules registered.
- `/docs` → 200 (excluded from JWT on purpose).
- `/mcp` → **401** — with `MCP_CONNECT_SECRET` set, plus a `WWW-Authenticate: Bearer resource_metadata="…"` header; without it a plain JSON 401. **200 means the endpoint is open — stop.**
- `/agents` → **401**. A 200 means `RUNTIME_ENV=dev` reached the synced env — stop and fix.
- Tell the user to hit **Connect** on the os.agno.com Live screen — the end-to-end proof.

Show what you verified, compactly.

## 6. Hand over

- code → `redeploy.sh`; config/secrets → edit `.env.production`, then `env-sync.sh`
- logs → the README's provider command
- teardown → `down.sh` (type the name to confirm; `--yes` skips)
- chat apps → claude.ai / ChatGPT connect to `https://<domain>/mcp` over OAuth; **print `MCP_CONNECT_SECRET` on its own line** (from the env file if the summary is gone). If none is set, say so: the web connectors cannot connect until it is.
- coding agents → `uvx agno connect --url https://<domain>`

## 7. Owned-infrastructure inversions

- **Key before first boot** — no control plane retries a keyless boot; do Step 4 into the env file first, then deploy.
- **The public URL is an input** — the user supplies it (ingress host, tunnel) and `AGENTOS_URL` must be set to it, or scheduled jobs never fire.
- **Check the aim** — on Kubernetes, confirm the kubectl context is the intended cluster before anything mutates.
