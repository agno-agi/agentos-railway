---
name: deploy-platform
description: Deploy this AgentOS to production with this template's deploy scripts — preflight the provider CLI and account, run the up.sh script, complete the JWT key step, verify the live platform on its public URL, then hand over the redeploy/logs/teardown instructions. Use this skill when the user asks to deploy, ship to production, go live, or take the platform to prod.
---

# Deploy the Platform

> _**Coding-agent workflow** — a `/slash-command` your coding agent (Claude Code, Codex, others) runs while developing this repo. Invoke it by name (e.g. `/deploy-platform`) or describe the task and it triggers automatically._

You are taking a locally-proven platform to a live public URL. Deploying creates real, billed cloud resources: say so before creating anything, and name the teardown script in the same breath.

**Be self-driving:** run every script and check yourself. Stop when progress needs a human: a provider login, a browser-only step, a key only they can mint. When you stop, give exact instructions, and tell the user to run interactive commands (logins, guided prompts) in a separate terminal window — not this chat; CLI logins need a real TTY and a browser. Never print or echo secret values; the two exceptions are the JWT verification key (a public key) and the MCP connect secret the up script prints in its own summary.

**Narrate the trip:** open with the map and the cost sentence together, shaped like this — tune the names to this repo and the mode you picked, keep the shape — then a line as each step starts and a word when it lands:

```text
Kicking off /deploy-platform. Here's the map for this trip:

1. Read the deploy layer — this repo's scripts + README, pick the mode
2. Preflight — provider CLI + login, cost and exit, production env
3. Deploy — the up script (compute + Postgres + public domain)
4. JWT key — connect os.agno.com Live, land the public key, sync it
5. Prove it live — logs, /docs 200, /mcp 401 challenge, UI Connect
6. Hand over — redeploy, logs, teardown, chat + coding-agent connect

One thing up front: this creates real, billed resources on your account.
The exit is always one command away — the down script deletes everything
(it asks you to confirm; --yes skips).
```

On a **redeploy** — Step 3's branch finds the platform already live — the map is three beats instead of six (push the change, prove it live, hand back), and the billed-resources sentence is already spent, so drop it.

## 1. Read the deploy layer

Read [`AGENTS.md`](../../../AGENTS.md), the README's production/deploy section, and the deploy scripts under `scripts/` — never invent a step they don't have. Then pick the mode by **who provisions the target**, not by which files exist:

- **Conduct** (this skill's main path): the up script provisions the compute *and* the public URL on a managed cloud provider (`up.sh`, `env-sync.sh`, `redeploy.sh`, `down.sh` under `scripts/<provider>/`).
- **Conduct over owned infra**: the same quartet exists, but it deploys onto infrastructure the user already owns (their own Kubernetes cluster and registry image). Drive the scripts like Conduct, with Step 7's inversions on top; the scripts themselves bill nothing.
- **Manual-guide**: no deploy quartet at all — self-hosted compose (`compose.prod.yaml`) on the user's own host. Say plainly that production here is a manual setup this skill guides but doesn't drive: walk the README's deploy section with them, carrying Step 4's key hand-off and Step 5's probes, with Step 7's inversions.

## 2. Preflight

Four checks before anything is created:

- **CLI + account.** Confirm the provider CLI the deploy scripts use is installed, and authed with a read-only probe (the scripts show which — a `whoami`-style command). Not logged in → stop, hand them the login command for a separate terminal window, and re-run the probe when they say ready.
- **Cost + exit.** One sentence: this creates billed resources on their account, and `down.sh` (typed-name confirm; `--yes` for automation) deletes everything.
- **Production env.** The env file the README names (usually `.env.production`; `cp example.env .env.production` if missing), with a real `OPENAI_API_KEY` — the up script refuses without it; help them set it the way setup-platform does (editor paste — never read or print it). `RUNTIME_ENV` must **not** be `dev` in this file: it syncs to the cloud, and `dev` there disables production auth.
- **Unattended-run inputs.** Read the up script for the provisioning calls it makes, and ask of each: does it name the account-level scope it acts in — the workspace, org, team, project, or region? Where the CLI infers that scope and the account has more than one option, the call opens a picker — failing outright on some CLIs, hanging on others. So list the options with the provider CLI first. Exactly one resolves cleanly and you're clear. More than one, with nothing in the script pinning it, means **stop before creating anything**: hand the user either the flag or env var that pins the scope, or the one interactive command to run in their own terminal (their CLI's init/link step, where the picker works), and continue when they confirm. Never let it resolve by guess — the project lands wherever the CLI's default points, bills that account, and the teardown script only finds it while this checkout stays linked to it.

## 3. Deploy

**First, is this a first deploy or a redeploy?** Read `AGENTOS_URL` out of the production env file and, if it names a real domain, probe `<domain>/docs`. A 200 means this platform is already live and the up script is the wrong tool — it *provisions*, and re-running it can create a second project with its own database and domain. Take the redeploy path instead:

- code changes → the redeploy script; env or secret changes → the env-sync script (both, in that order, if both changed)
- skip Step 4 — the key already landed; Step 5's probes will say so if it didn't
- run Step 5 as written, then Step 6 — verification is the same either way
- manual-guide mode has no redeploy script: use the README's update path

No answer from the probe — DNS failure, connection refused — means nothing is serving there (a torn-down project, a stale `AGENTOS_URL`): say so, and continue as a first deploy.

Otherwise, run the up script. Every pause the script itself owns is TTY-guarded, so under your shell it skips or stops cleanly and prints its recovery path instead of hanging. Narrate the phases as they stream. Expectations to set:

- First creates can be slow on some providers — twenty-plus minutes is normal; keep polling.
- If the README names a browser step (e.g. applying a blueprint in the provider dashboard), relay those instructions first, then start the up script — its own poll absorbs the wait for the click.
- When it finishes, read the live URL back from `AGENTOS_URL` in the env file — the script persisted the domain there. Its closing summary also prints the `MCP_CONNECT_SECRET` — hold onto it for Step 6.
- **A keyless first deploy refusing to start is by design:** with production auth on and no JWT key, the app exits at startup, so the provider dashboard shows the deploy failing or restarting until the key lands in the next step. Tell the user before they see it. Then check the provider logs yourself (the README names the command; bound the read with a lines/limit flag — streaming forms run forever) and confirm the startup error is the missing JWT key — any other error, fix it first.

## 4. The JWT key

The platform is deployed and waiting for its key. Tell the user plainly: the deploy landed, but the platform isn't live *yet* — it ships with authorization on, and this key is the one piece only they can add; the moment it lands, the platform comes up on its own. The message that asks for the key carries everything they need — render the table and the mint path fresh in that same message, even if you showed them earlier; never say "see the table above".

The connection:

| Setting | Value |
|---|---|
| AgentOS UI | https://os.agno.com |
| Connection type | **Live** |
| Endpoint | `https://<the AGENTOS_URL domain>` |
| Name | `Live AgentOS` |

Then the mint path, spelled out as numbered clicks:

1. **Connect OS** → **Live** → enter the endpoint from the table → name it. (Live connections are a paid feature — `PLATFORM30` takes a month off.)
2. Flip **Token-Based Authorization (JWT)** on — the toggle is right on the connect panel — then **Connect**. The UI generates the public key; copy it, that's the one we need.
3. Already connected, or can't find the toggle? **Settings → OS & Security → Token-Based Authorization (JWT)** — turn it on there and copy the key. Always mention this fallback.

The up script prints its own abbreviated copy of these clicks at its key pause. **The clicks above are canonical** — the README's deploy section and `AGENTS.md` agree on them. If the script's copy differs, relay this path and note the drift in your hand-over rather than pasting both.

Then offer both hand-offs, their choice:

- **paste the key right here in chat** — it's a public verification key, safe to share — and you write it into `.env.production` yourself, or
- **paste it into `.env.production`** on the `JWT_VERIFICATION_KEY=` line and say ready.

Either way the PEM must land **quoted, with its own line breaks** — multi-line inside the quotes, as the README's example shows; an unquoted or newline-collapsed PEM breaks parsing. Then push it with `env-sync.sh` — it applies the change itself (a restart, new revision, or deploy, depending on the provider); confirm from its closing message.

And name the one honest alternative in the same message, clearly not recommended: authorization *can* be turned off — the README's opt-out is `authorization=False` in `app/main.py`, then redeploy; the scripts refuse to sync `RUNTIME_ENV=dev` unless `ALLOW_UNAUTHENTICATED_DEPLOY=1` is set — but that makes the AgentOS public: anyone with the URL can run the agents and read the data.

## 5. Prove it live

Every probe goes to the **public domain**, never localhost — a localhost check can pass while the deployed endpoint is broken:

- Provider logs (bounded read): clean boot, no tracebacks, schedules registered.
- `https://<domain>/docs` → 200. This works even with auth on — the JWT middleware deliberately excludes it.
- `https://<domain>/mcp` → **401**: mounted *and* gated. Two 401s are both correct: with `MCP_CONNECT_SECRET` set (the usual case — the up script generates one), the MCP layer answers the RFC 9728 challenge, `401` plus a `WWW-Authenticate: Bearer resource_metadata="…"` header; without it, production JWT answers with a plain JSON `401` and no `WWW-Authenticate` — gated, just not connector-discoverable. Check the header only when OAuth is on; check the status code always. A **200 means the endpoint is wide open** — stop and find out why.
- An API route, e.g. `https://<domain>/agents` → **401**. This is the dev-leak tripwire: a 200 means JWT is off — `RUNTIME_ENV=dev` reached the synced env; stop and fix.
- Tell the user to hit **Connect** on the os.agno.com Live screen from Step 4 — the UI connecting over real auth is the end-to-end proof, and where they chat with the live platform.

Close the step by showing what you verified, compactly.

## 6. Hand over the loop

Finish with what they own now:

- code changes → `redeploy.sh`; config or secret changes → edit `.env.production`, then `env-sync.sh`
- logs → the provider command from the README
- teardown → `down.sh` (type the resource name it shows to confirm; `--yes` skips the prompt)
- chat apps → connect claude.ai / ChatGPT to `https://<domain>/mcp` over OAuth; the consent secret is `MCP_CONNECT_SECRET` — **print its value on its own line here** (read it out of the env file if the up script's summary is gone). If the env file has none, say so plainly: the web connectors authenticate over OAuth only, so until that secret is set and synced, claude.ai and ChatGPT cannot connect at all, however valid the PATs are.
- coding agents → `uvx agno connect --url https://<domain>`

## 7. Owned-infrastructure inversions

These apply on top of Steps 2–6 whenever the target is infrastructure the user owns (the second and third modes from Step 1):

- **Get the key in before the first boot.** On owned infra there's no managed control plane retrying a keyless boot — the install crash-loops or times out its wait. Do Step 4's key hand-off first, into the env file the README names, then deploy.
- **The public URL is an input, not an output.** Nothing provisions a domain here; the user supplies one (an ingress host, a tunnel), and `AGENTOS_URL` must be set to it or scheduled jobs silently never fire.
- **Check the aim before anything mutates.** On Kubernetes, confirm the current kubectl context is the intended cluster — a non-interactive deploy lands wherever the context points.
