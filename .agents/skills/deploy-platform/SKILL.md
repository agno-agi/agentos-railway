---
name: deploy-platform
description: Deploy this AgentOS using its own provider instructions, configure JWT verification, and verify the public service. Use for first deployment, redeployment, or production configuration changes.
---

# Deploy the Platform

Read `AGENTS.md`, the README deployment section, and this repository's deploy
configuration and scripts. Use those files to identify the provider and its exact
commands, required CLI versions, environment file, and teardown behavior.
Do not assume every template has deploy scripts or supports the same flags.
For Docker or an existing Kubernetes cluster, follow the repository's Compose or
Helm instructions.

Never print credentials or the MCP connect secret. The JWT verification key is
public and may be shared to complete configuration.

## 1. Prepare

- Check the required tools and the authenticated provider account. Interactive
  logins belong in the user's terminal.
- Confirm the intended workspace, account, project, region, or cluster context
  before making changes. Use the inputs required by this repository's commands.
- Set up the project environment if the deploy scripts need it. Use the production
  env file documented in the README; create it from `example.env` only if absent.
  Configure credentials without printing them. Check how the deploy scripts load
  settings rather than assuming they read `.env` or exported shell variables.
- Keep production authentication enabled. Do not upload `RUNTIME_ENV=dev`.
  Configure `JWT_VERIFICATION_KEY` or a `JWT_JWKS_FILE` available on the server.
- If a sandbox is requested, configure its provider and `REPOSITORY` in
  `app/sandbox.py` using the [sandbox setup guide](../../../docs/sandboxes.md).
  AgentCore needs an existing runtime, host AWS access, and persistent checkpoints at `/data`. Confirm the
  deployment target supports that mount before enabling it. Use volume flags only
  if this repository's deploy scripts support them. Bedrock settings and private
  repository credentials must be supplied explicitly through the provider's `env`.
  Never put secret values in source.
- Remove retired `SANDBOX_ENABLED`, `SANDBOX_IMAGE`, and `SANDBOX_RUNTIME_ARN`
  settings; they no longer select a provider. Keep one API replica and the
  always-running process needed by the scheduler.

## 2. Choose first deployment or update

Use the provider's status/list commands, saved project identifiers, and local
configuration to find an existing deployment. A failed health check does not mean
its resources are gone. Resolve authentication, permission, and network errors
before deciding to create anything. Link an existing project where required.

For a new deployment, explain which resources will be created, their billing,
and the actual teardown command and data it deletes. Run the README's first-deploy
procedure with the intended account and target explicitly selected.
For owned infrastructure, configure its public URL and JWT key before first boot.

For an update, follow the README's code and environment update commands. Read the
scripts to establish their order and whether updating settings also triggers a
redeploy. Use flags such as `--no-deploy` only when implemented by that script.
If a command fails, inspect existing resources and any partial settings changes
before retrying. Do not create a second project to recover from a failed deploy.

## 3. Complete authentication and settings

Some providers create a URL before the API can start. Follow this repository's
handoff: use that URL to connect a Live OS at https://os.agno.com, enable token-based
JWT authorization, and obtain the public verification key. Save the full key as a
quoted multiline `JWT_VERIFICATION_KEY` in the production settings, or configure
`JWT_JWKS_FILE`. Then use the documented sync/deploy commands to finish.
Do not treat an exit code or missing-key stop as identical across providers.

Ensure `AGENTOS_URL` is the public HTTPS URL used by the scheduler and MCP OAuth.
Keep `MCP_CONNECT_SECRET` in the production settings for browser MCP connections.
Check how this provider clears remote variables; removing a local line may not
remove the saved value. Database credential rotation is separate from updating
API settings. Disable a sandbox by returning `None` from `sandbox_provider()` and
redeploying.

## 4. Verify and hand over

Build submission is not successful deployment. Inspect bounded provider logs and
test the public URL: `/health` must succeed; unauthenticated `/agents` requests and
MCP initialization POSTs must reject access. A plain `GET /mcp` may return public
server-card metadata; it does not test authorization. With MCP OAuth enabled,
verify the POST's Bearer challenge. Exercise an authenticated request with an
existing token, then confirm the UI connects.

Model prompts spend calls; report exactly what ran. Engineer HTTP runs, delegation,
and Company Task completion need separate verification before claiming they work.

Provide the URL, verification results, and this repository's commands for code
updates, settings, logs, and teardown. For browser MCP, use `<AGENTOS_URL>/mcp` and
tell the user to enter `MCP_CONNECT_SECRET` from the production settings into the
consent page; do not print it. For coding clients, use
`uvx agno connect --url <AGENTOS_URL>`.
