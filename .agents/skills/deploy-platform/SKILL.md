---
name: deploy-platform
description: Deploy this AgentOS on Railway using the shared deployment CLI, configure JWT verification, and verify the public service. Use for first deployment, redeployment, or production configuration changes.
---

# Deploy the Platform

Read `AGENTS.md`, the README deployment section and `scripts/railway/deploy.py`.
Use the existing scripts. Never print credentials or the MCP connect secret.
The JWT verification key is public and may be shared to complete configuration.

## 1. Prepare

- Confirm Railway CLI 5.49.0 or newer and an authenticated account with `railway whoami`.
  A login must run in the user's interactive terminal.
- Run `./scripts/venv_setup.sh` if the project environment is absent or stale.
- Copy `example.env` to `.env.production` only if absent. Configure its OpenAI key
  without printing it. The scripts read this file, not `.env` or exported application
  variables. Quoted multiline PEMs are supported; shell expansion is disabled.
- Require `RUNTIME_ENV=prd` (also the default). There is no unauthenticated deploy mode.
- For AgentCore, provision the runtime through AWS tooling first and return
  `agentcore_sandbox("your-runtime-arn")` from `sandbox_provider()` in `app/sandbox.py`.
  Configure host AWS credentials. For Bedrock, explicitly set the provider's `env`
  mapping and Claude's model as described in the README; no cloud flags or private-repo
  credentials are forwarded automatically. Never put secret values in source.
- The API needs `/data` for AgentCore checkpoints. Add `--with-checkpoint-volume` to
  first provisioning. On an existing deployment, create that mount before redeploying
  the provider change. Remove retired `SANDBOX_ENABLED`, `SANDBOX_IMAGE` and
  `SANDBOX_RUNTIME_ARN` values from production env files; they no longer select a provider.

## 2. Determine whether the project exists

Run `railway status --json` from the repository root. A linked project uses the update
path even if its API is down. An authentication, permission or network error is not
proof that no project exists: resolve it before proceeding. If an existing deployment
is not linked, use `railway link` rather than creating another project.

For a new project, resolve the user's exact Railway workspace. State that provisioning
creates billed resources and that `./scripts/railway/down.sh` deletes the entire project,
including its database and volumes. Then run:

```sh
./scripts/railway/up.sh --workspace <workspace-name-or-id>
```

The script saves generated settings in the production file, uploads all configuration,
and submits the application build only when JWT verification is configured.
If provisioning fails, inspect the linked project before retrying; do not create a duplicate.

## 3. Complete JWT configuration

Exit 2 from `up.sh` means resources exist but the API has not been deployed. Use the
saved `AGENTOS_URL` to connect a Live OS at https://os.agno.com/?ref=railway-template, enable token-based
JWT authorization and obtain the public verification key. Save it as a quoted multiline
`JWT_VERIFICATION_KEY` in `.env.production`, or configure a deployed `JWT_JWKS_FILE`.
Then finish:

```sh
./scripts/railway/env-sync.sh --no-deploy
./scripts/railway/redeploy.sh
```

For updates: code only → `redeploy.sh`; settings only → `env-sync.sh`; both → sync
with `--no-deploy` first, then redeploy. Failed uploads may leave partial settings but
never trigger deployment; fix and rerun. Omitted keys remain remote. Set optional
credentials to empty, or explicitly remove them through Railway to disable them.
Disable a sandbox by returning `None` from `sandbox_provider()` and redeploying.
PostgreSQL credential rotation is a separate operation; env sync updates the API service.

## 4. Verify and hand over

Build submission is not successful deployment. Inspect bounded provider logs and the
public URL: `/health` must succeed; unauthenticated `/agents` and MCP initialization
POSTs must reject access. A plain `GET /mcp` may return public server-card metadata;
it does not test authorization. With MCP OAuth enabled, verify the POST's Bearer
challenge. Exercise an authenticated
request with an existing token, then confirm the UI connects. Model prompts spend calls;
report exactly what ran. Engineer HTTP runs, delegation and Company Task completion
need their own verification before claiming those capabilities work.

Provide the URL, verification results, and the README commands for code updates, settings,
logs and teardown. For browser MCP, use `<AGENTOS_URL>/mcp` and tell the user to enter
`MCP_CONNECT_SECRET` from the production file into the consent page; do not print it.
For coding clients, use `uvx agno connect --url <AGENTOS_URL>`.
