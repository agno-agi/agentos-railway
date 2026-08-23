#!/bin/bash

############################################################################
#
#    Agno Railway Setup (first-time provisioning)
#
#    Usage:     ./scripts/railway/up.sh
#    Redeploy:  ./scripts/railway/redeploy.sh
#    Sync env:  ./scripts/railway/env-sync.sh
#    Teardown:  ./scripts/railway/down.sh
#
#    Prerequisites:
#      - Railway CLI installed
#      - Logged in via `railway login`
#      - OPENAI_API_KEY set in environment (or .env / .env.production)
#
#    Optional environment:
#      RAILWAY_WORKSPACE            workspace to create the project in; needed
#                                   non-interactively when the account has more
#                                   than one, since `railway init` would prompt
#      ALLOW_UNAUTHENTICATED_DEPLOY set to 1 to deploy with RUNTIME_ENV=dev,
#                                   which serves the public domain with auth off
#
#    Creates the public domain before deploy, writes it to AGENTOS_URL,
#    generates MCP_CONNECT_SECRET (chat-app OAuth) into the env file when
#    missing, and pauses for JWT_VERIFICATION_KEY/JWT_JWKS_FILE when
#    production auth would otherwise prevent the first deploy from serving.
#
############################################################################

set -e

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
RED='\033[31m'
NC='\033[0m'

echo ""
echo -e "${ORANGE}"
cat << 'BANNER'
     █████╗  ██████╗ ███╗   ██╗ ██████╗
    ██╔══██╗██╔════╝ ████╗  ██║██╔═══██╗
    ███████║██║  ███╗██╔██╗ ██║██║   ██║
    ██╔══██║██║   ██║██║╚██╗██║██║   ██║
    ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝
BANNER
echo -e "${NC}"

# Persist a resolved single-line value back into the env file so it stays a
# faithful record of the deploy (and env-sync.sh keeps managing it). Replaces
# an existing commented-or-uncommented `KEY=` line in place; appends if the key
# is absent. Rewrites via the original file (not `mv`) so the file keeps its
# inode + permissions. The `|` sed delimiter avoids clashing with URL slashes.
# No-op when the file is missing.
persist_env_var() {
    local key="$1" value="$2" file="$3" tmp
    [[ -z "$file" || ! -f "$file" ]] && return
    if grep -qE "^[#[:space:]]*${key}=" "$file"; then
        tmp="$(mktemp)"
        if sed -E "s|^[#[:space:]]*${key}=.*|${key}=${value}|" "$file" > "$tmp"; then
            cat "$tmp" > "$file"
        fi
        rm -f "$tmp"
    else
        printf '\n%s=%s\n' "$key" "$value" >> "$file"
    fi
}

# Persist a multi-line env value. Existing active KEY= blocks are removed before
# appending the new value; commented examples are left alone as documentation.
persist_multiline_env_var() {
    local key="$1" value="$2" file="$3" tmp line skipping=0 value_part
    [[ -z "$file" ]] && return
    if [[ ! -f "$file" ]]; then
        printf '%s="%s"\n' "$key" "$value" > "$file"
        return
    fi

    # Values are written quoted so compose's env_file parser (and every script
    # parser here, which strips quotes) reads the multi-line PEM as one variable.
    tmp="$(mktemp)"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$skipping" == 1 ]]; then
            [[ "$line" == *"-----END"* ]] && skipping=0
            continue
        fi

        if [[ "$line" =~ ^[[:space:]]*${key}= ]]; then
            value_part="${line#*=}"
            if [[ "$value_part" == *"-----BEGIN"* && "$value_part" != *"-----END"* ]]; then
                skipping=1
            fi
            continue
        fi

        printf '%s\n' "$line" >> "$tmp"
    done < "$file"

    [[ -s "$tmp" ]] && printf '\n' >> "$tmp"
    printf '%s="%s"\n' "$key" "$value" >> "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

# Load env file — .env.production preferred for Railway, .env as fallback.
# Parsed line-by-line (not `source`d) so an unquoted multi-line PEM
# JWT_VERIFICATION_KEY isn't interpreted as shell. Mirrors the parser in
# env-sync.sh so both scripts read .env files identically. A function so
# the JWT pause below can re-read the file after the user edits it.
load_env_file() {
    local line current_key="" current_value=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$current_key" ]]; then
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        fi

        if [[ -z "$current_key" ]]; then
            current_key="${line%%=*}"
            current_value="${line#*=}"
        else
            current_value="${current_value}
${line}"
        fi

        # Still inside a PEM block — keep accumulating lines.
        if [[ "$current_value" == *"-----BEGIN"* && "$current_value" != *"-----END"* ]]; then
            continue
        fi

        # Strip surrounding quotes if present
        current_value="${current_value#\"}"
        current_value="${current_value%\"}"
        current_value="${current_value#\'}"
        current_value="${current_value%\'}"

        export "${current_key}=${current_value}"

        current_key=""
        current_value=""
    done < "$1"
}

# shellcheck disable=SC2034
capture_pasted_jwt_verification_key() {
    local first_line="$1" line pasted="$1"

    pasted="${pasted#export JWT_VERIFICATION_KEY=}"
    pasted="${pasted#JWT_VERIFICATION_KEY=}"
    [[ "$pasted" != *"-----BEGIN"* ]] && return 1

    while [[ "$pasted" != *"-----END"* ]]; do
        if ! IFS= read -r line; then
            break
        fi
        pasted="${pasted}
${line}"
    done

    [[ "$pasted" != *"-----BEGIN"* || "$pasted" != *"-----END"* ]] && return 1

    pasted="${pasted#\"}"
    pasted="${pasted%\"}"
    pasted="${pasted#\'}"
    pasted="${pasted%\'}"

    JWT_VERIFICATION_KEY="$pasted"
    export JWT_VERIFICATION_KEY
}

ENV_FILE=""
[[ -f .env.production ]] && ENV_FILE=".env.production"
[[ -z "$ENV_FILE" && -f .env ]] && ENV_FILE=".env"

if [[ -n "$ENV_FILE" ]]; then
    load_env_file "$ENV_FILE"
    echo -e "${DIM}Loaded ${ENV_FILE}${NC}"
fi

# Preflight — everything that must hold before the first billable resource
# exists. A check that only fires later costs the user a half-provisioned
# project they then have to find and delete by hand.
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Install: https://docs.railway.com/cli#installing-the-cli"
    exit 1
fi

if ! railway whoami &> /dev/null; then
    echo "Not logged in to Railway. Run: railway login"
    exit 1
fi

if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "OPENAI_API_KEY not set. Add to .env (or .env.production) or export it."
    exit 1
fi

# openssl backs only the MCP_CONNECT_SECRET generation further down, so a
# missing one skips that step rather than aborting an otherwise fine deploy —
# but say it here, while installing it is still cheap, not in the summary.
if ! command -v openssl &> /dev/null; then
    echo -e "${DIM}openssl not found — MCP_CONNECT_SECRET won't be generated. Set it yourself if you${NC}"
    echo -e "${DIM}want claude.ai / ChatGPT to connect over OAuth; everything else deploys normally.${NC}"
fi

# app/main.py passes `authorization=runtime_env != "dev"`, so the literal string
# `dev` is the single value that turns production auth off — and compose sets
# exactly that for local work, which makes `cp .env .env.production` the way a
# public, unauthenticated platform gets deployed by accident. Catch it here,
# before anything is provisioned, and make the operator say it out loud.
if [[ "$RUNTIME_ENV" == "dev" ]]; then
    echo ""
    echo -e "${RED}${BOLD}RUNTIME_ENV=dev${NC} — this deploy would serve the public Railway domain with"
    echo -e "${RED}${BOLD}authorization switched off.${NC} Anyone who has the URL could run your agents,"
    echo -e "spend your OpenAI key, and read every session in the database."
    echo ""
    echo -e "${DIM}  Fix: remove RUNTIME_ENV from ${ENV_FILE:-your env file} — it defaults to prd.${NC}"
    echo -e "${DIM}  Or set ALLOW_UNAUTHENTICATED_DEPLOY=1 if an open platform is what you want${NC}"
    echo -e "${DIM}  (throwaway E2E deploys that skip JWT minting are the reason that exists).${NC}"
    if [[ "$ALLOW_UNAUTHENTICATED_DEPLOY" == "1" ]]; then
        echo ""
        echo -e "${BOLD}ALLOW_UNAUTHENTICATED_DEPLOY=1 — continuing with auth off.${NC}"
    elif [[ -t 0 ]]; then
        echo ""
        printf "Type 'unauthenticated' to deploy anyway: "
        IFS= read -r DEV_CONFIRM || true
        if [[ "$DEV_CONFIRM" != "unauthenticated" ]]; then
            echo "Aborted — nothing was provisioned."
            exit 1
        fi
    else
        echo ""
        echo "Aborted — nothing was provisioned."
        exit 1
    fi
fi

# Flags whose availability varies by CLI version. Probed once from --help so an
# older railway binary degrades instead of dying on an unknown argument.
INIT_SUPPORTS_WORKSPACE=""
railway init --help 2>&1 | grep -q -- '--workspace' && INIT_SUPPORTS_WORKSPACE=1
VAR_SET_FLAGS=()
railway variables --help 2>&1 | grep -q -- '--skip-deploys' && VAR_SET_FLAGS=(--skip-deploys)

# `railway list` prints each workspace flush-left with its projects indented
# beneath, so the unique unindented lines are the workspace names. A workspace
# holding no projects never appears, which makes this a lower bound: enough to
# prove an interactive prompt is coming, never enough to prove one isn't.
railway_workspaces() {
    railway list 2> /dev/null | grep -E '^[^[:space:]]' | sort -u
}

# `railway init` asks which workspace to create the project in whenever the
# account has more than one, and that prompt has no answer on a non-interactive
# stdin — which is how an agent-driven or CI deploy stalls here. RAILWAY_WORKSPACE
# names one up front; without it, refuse early rather than at the prompt.
INIT_ARGS=(-n "agentos-railway")
if [[ -n "$RAILWAY_WORKSPACE" ]]; then
    if [[ -n "$INIT_SUPPORTS_WORKSPACE" ]]; then
        INIT_ARGS+=(-w "$RAILWAY_WORKSPACE")
    else
        echo -e "${BOLD}Warning:${NC} this Railway CLI's init has no --workspace flag, so RAILWAY_WORKSPACE"
        echo -e "${DIM}  is ignored. Run 'railway upgrade' if init stops on a workspace prompt.${NC}"
    fi
elif [[ ! -t 0 ]] && [[ "$(railway_workspaces | grep -c .)" -gt 1 ]]; then
    echo "This account has more than one Railway workspace, so 'railway init' will ask which"
    echo "one to use — and stdin isn't a terminal, so nothing can answer it. Name the workspace:"
    echo ""
    railway_workspaces | sed 's/^/  /'
    echo ""
    echo "  RAILWAY_WORKSPACE=\"<name>\" ./scripts/railway/up.sh"
    exit 1
fi

# Everything from `railway init` on is billing, so a later failure — a rejected
# variable push, a Ctrl-C at the JWT paste — leaves real resources behind. Say
# so at the point of exit instead of leaving the user to discover them.
PROVISIONING_STARTED=""
provisioning_abort_hint() {
    [[ "$1" == 0 || -z "$PROVISIONING_STARTED" ]] && return 0
    echo ""
    echo -e "${RED}${BOLD}Stopped after provisioning started${NC} — the Railway project exists and is billing."
    echo -e "${DIM}  Inspect:    railway status${NC}"
    echo -e "${DIM}  Finish it:  ./scripts/railway/env-sync.sh && ./scripts/railway/redeploy.sh${NC}"
    echo -e "${DIM}  Remove it:  ./scripts/railway/down.sh${NC}"
}
trap 'provisioning_abort_hint $?' EXIT
trap 'exit 130' INT

# Push one variable to the agent-os service. stdout is dropped so a value the
# CLI echoes back never reaches the terminal or a captured deploy log; stderr is
# kept, because the old `> /dev/null 2>&1` hid a failed OPENAI_API_KEY push
# behind a project that was already billing, and hid a failed MCP_CONNECT_SECRET
# push behind a summary that still printed the secret. The error text is
# scrubbed of the value first, so a CLI that echoes the pair on failure can't
# leak it either.
set_service_var() {
    local key="$1" value="$2" err status=0
    # `< /dev/null` keeps the CLI off this script's own stdin — the JWT step
    # reads a pasted PEM straight from the terminal, and a CLI that ever decides
    # to prompt would eat a line of it.
    err="$(railway variables --set "${key}=${value}" --service agent-os "${VAR_SET_FLAGS[@]}" \
        2>&1 > /dev/null < /dev/null)" || status=$?
    if [[ "$status" != 0 ]]; then
        echo -e "${RED}${BOLD}Failed to set ${key}${NC} on the agent-os service (railway exited ${status})."
        [[ -n "$err" ]] && echo -e "${DIM}  ${err//${value}/<value hidden>}${NC}"
        return 1
    fi
}

echo -e "${ORANGE}▸${NC} ${BOLD}Initializing project${NC}"
echo ""
if ! railway init "${INIT_ARGS[@]}"; then
    echo ""
    echo -e "${BOLD}railway init failed.${NC} If it stopped on a workspace prompt, name the workspace"
    echo "and re-run — these are the ones this account has projects in:"
    echo ""
    railway_workspaces | sed 's/^/  /'
    echo ""
    echo "  RAILWAY_WORKSPACE=\"<name>\" ./scripts/railway/up.sh"
    exit 1
fi
PROVISIONING_STARTED=1

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Deploying PgVector database${NC}"
echo ""
railway add -s pgvector -i agnohq/pgvector:18 \
    -v "POSTGRES_USER=${DB_USER:-ai}" \
    -v "POSTGRES_PASSWORD=${DB_PASS:-ai}" \
    -v "POSTGRES_DB=${DB_DATABASE:-ai}"

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Adding database volume${NC}"
railway service link pgvector
railway volume add -m /var/lib/postgresql 2>/dev/null || echo -e "${DIM}Volume already exists or skipped${NC}"

echo ""
echo -e "${DIM}Waiting 15s for database...${NC}"
sleep 15

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Creating application service${NC}"
echo ""
# Forward relevant env vars the first deploy might need.
# Use ./scripts/railway/env-sync.sh to sync the rest from .env later.
#
# Secrets (OPENAI_API_KEY) are deliberately NOT passed via
# `railway add -v`: the CLI's non-interactive `add` echoes every `-v` value to
# stdout, so the API key would print in cleartext (and into any captured deploy
# log). They go in below via `railway variables --set … > /dev/null`, which is
# quiet — the same path already used for AGENTOS_URL / JWT.
RAILWAY_VARS=(
    -v "DB_USER=${DB_USER:-ai}"
    -v "DB_PASS=${DB_PASS:-ai}"
    -v "DB_HOST=pgvector.railway.internal"
    -v "DB_PORT=${DB_PORT:-5432}"
    -v "DB_DATABASE=${DB_DATABASE:-ai}"
    -v "DB_DRIVER=postgresql+psycopg"
    -v "WAIT_FOR_DB=True"
    -v "PORT=8000"
)
[[ -n "$RUNTIME_ENV" ]] && RAILWAY_VARS+=(-v "RUNTIME_ENV=${RUNTIME_ENV}")
[[ -n "$JWT_JWKS_FILE" ]] && RAILWAY_VARS+=(-v "JWT_JWKS_FILE=${JWT_JWKS_FILE}")
# Forward AGENTOS_URL only if the env file already pinned one; otherwise it's
# derived from the fresh domain below.
[[ -n "$AGENTOS_URL" ]] && RAILWAY_VARS+=(-v "AGENTOS_URL=${AGENTOS_URL}")

railway add -s agent-os "${RAILWAY_VARS[@]}"

# Secret vars, set quietly so their values never show up in the terminal or logs.
# OPENAI_API_KEY is fatal: without it the service boots into a platform that
# can't answer, so stop here (the abort hint above names the teardown) rather
# than build an image around a missing key. A missing PARALLEL_API_KEY only
# drops web search to its keyless fallback, so that one warns and continues.
set_service_var OPENAI_API_KEY "$OPENAI_API_KEY"
if [[ -n "$PARALLEL_API_KEY" ]]; then
    set_service_var PARALLEL_API_KEY "$PARALLEL_API_KEY" \
        || echo -e "${DIM}  Web search falls back to the keyless MCP path until you sync it.${NC}"
fi

# Domain before deploy — capture it so AGENTOS_URL is set on the service
# *before* it serves, and so os.agno.com can mint JWT_VERIFICATION_KEY against
# the real domain.
echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Creating domain${NC}"
echo ""
DOMAIN_OUTPUT="$(railway domain --service agent-os 2>&1 || true)"
echo "$DOMAIN_OUTPUT"
APP_URL="$(grep -oE 'https://[A-Za-z0-9.-]+|[A-Za-z0-9-]+\.up\.railway\.app' <<< "$DOMAIN_OUTPUT" | head -1)"
[[ -n "$APP_URL" && "$APP_URL" != https://* ]] && APP_URL="https://${APP_URL}"

# The scheduler reaches AgentOS over its public URL. Without AGENTOS_URL it
# defaults to http://127.0.0.1:8000, so scheduled jobs silently never fire in
# prod. Default it to the fresh domain (unless the env file pinned one), and
# write it back into the env file so .env.production stays a faithful record
# and env-sync.sh keeps managing it.
AGENTOS_URL_PERSISTED=""
if [[ -z "$AGENTOS_URL" && -n "$APP_URL" ]]; then
    set_service_var AGENTOS_URL "$APP_URL"
    persist_env_var AGENTOS_URL "$APP_URL" "$ENV_FILE"
    [[ -n "$ENV_FILE" ]] && AGENTOS_URL_PERSISTED=1
    echo -e "${DIM}Set AGENTOS_URL=${APP_URL} (Railway${AGENTOS_URL_PERSISTED:+ + ${ENV_FILE}})${NC}"
elif [[ -z "$AGENTOS_URL" ]]; then
    # Domain creation/parse failed and nothing was pinned — don't ship silently
    # with the localhost default, or scheduled jobs will never fire in prod.
    echo -e "${BOLD}Warning:${NC} couldn't determine the Railway domain, so AGENTOS_URL is unset."
    echo -e "${DIM}  Scheduled jobs won't reach AgentOS until you set it. Once the domain is live:${NC}"
    echo -e "${DIM}  railway variables --set AGENTOS_URL=https://<your-domain> --service agent-os${NC}"
    echo -e "${DIM}  (or add it to ${ENV_FILE:-.env.production} and run ./scripts/railway/env-sync.sh)${NC}"
fi

# MCP OAuth — claude.ai and ChatGPT (web) connect over OAuth only, and the
# consent page is gated by MCP_CONNECT_SECRET, so the user must create the secret manually.
# We generate a secret on behalf of the user when the env file doesn't have one
if [[ -z "$MCP_CONNECT_SECRET" && ( -n "$AGENTOS_URL" || -n "$APP_URL" ) ]] && command -v openssl &> /dev/null; then
    MCP_CONNECT_SECRET="$(openssl rand -base64 32)"
    export MCP_CONNECT_SECRET
    ENV_FILE="${ENV_FILE:-.env.production}"
    [[ -f "$ENV_FILE" ]] || : > "$ENV_FILE"
    persist_env_var MCP_CONNECT_SECRET "$MCP_CONNECT_SECRET" "$ENV_FILE"
    echo -e "${DIM}Generated MCP_CONNECT_SECRET -> ${ENV_FILE} + Railway (shown in the summary below)${NC}"
fi
# Tracked, not assumed: the summary below tells the user to approve a consent
# page with this secret, and printing that instruction after a push Railway
# rejected sends them to a connector that will never authenticate.
MCP_SECRET_ON_RAILWAY=""
if [[ -n "$MCP_CONNECT_SECRET" ]]; then
    if set_service_var MCP_CONNECT_SECRET "$MCP_CONNECT_SECRET"; then
        MCP_SECRET_ON_RAILWAY=1
    else
        echo -e "${DIM}  It's saved in ${ENV_FILE:-your env file} — run ./scripts/railway/env-sync.sh to retry.${NC}"
        echo -e "${DIM}  Until it lands, /mcp stays closed to claude.ai and ChatGPT (web).${NC}"
    fi
fi

AUTH_REQUIRES_JWT=1
[[ "${RUNTIME_ENV:-prd}" == "dev" ]] && AUTH_REQUIRES_JWT=""

# JWT auth is on in prd and the app refuses to serve without either a PEM
# verification key or a JWKS file. Now that the domain exists, the user can
# mint the key, save it, and have this first deploy come up serving.
if [[ -n "$AUTH_REQUIRES_JWT" && -z "$JWT_VERIFICATION_KEY" && -z "$JWT_JWKS_FILE" && -t 0 ]]; then
    echo ""
    echo -e "${ORANGE}▸${NC} ${BOLD}JWT_VERIFICATION_KEY not set${NC} — AgentOS won't serve production traffic without auth."
    echo -e "  1. Open ${BOLD}https://os.agno.com${NC} -> Connect OS -> Live -> enter ${APP_URL:-your Railway domain}"
    echo -e "  2. Name it ${BOLD}Live AgentOS${NC}"
    echo -e "  3. Note: Live AgentOS Connections are a paid feature; use ${BOLD}PLATFORM30${NC} to get 1 month off"
    echo -e "  4. Flip ${BOLD}Token-Based Authorization (JWT)${NC} on — the toggle is on the connect panel"
    echo -e "     (already connected without it? Settings -> OS & Security)"
    echo -e "  5. Copy the public key"
    echo -e "  6. Paste the full PEM block at the prompt below, or save it in ${ENV_FILE:-.env.production}"
    echo -e "     Or set JWT_JWKS_FILE if you mount a JWKS file in the image."
    [[ -n "$AGENTOS_URL_PERSISTED" ]] && echo -e "  ${DIM}(AGENTOS_URL was already written to ${ENV_FILE} for you.)${NC}"
    echo ""
    echo -e "  Paste JWT_VERIFICATION_KEY now, or press Enter after saving it:"
    JWT_INPUT=""
    IFS= read -r JWT_INPUT || true
    if [[ -n "$JWT_INPUT" ]]; then
        if capture_pasted_jwt_verification_key "$JWT_INPUT"; then
            ENV_FILE="${ENV_FILE:-.env.production}"
            persist_multiline_env_var JWT_VERIFICATION_KEY "$JWT_VERIFICATION_KEY" "$ENV_FILE"
            echo -e "${DIM}  Saved JWT_VERIFICATION_KEY to ${ENV_FILE}${NC}"
        else
            echo -e "${BOLD}Warning:${NC} couldn't parse the pasted JWT_VERIFICATION_KEY."
            echo -e "${DIM}  Save it to ${ENV_FILE:-.env.production} and run ./scripts/railway/env-sync.sh if auth is still missing.${NC}"
        fi
    else
        [[ -f .env.production ]] && ENV_FILE=".env.production"
        [[ -z "$ENV_FILE" && -f .env ]] && ENV_FILE=".env"
    fi
    [[ -n "$ENV_FILE" ]] && load_env_file "$ENV_FILE"
fi

if [[ -n "$JWT_VERIFICATION_KEY" ]]; then
    echo ""
    echo -e "${DIM}Setting JWT_VERIFICATION_KEY${NC}"
    set_service_var JWT_VERIFICATION_KEY "$JWT_VERIFICATION_KEY"
elif [[ -n "$JWT_JWKS_FILE" ]]; then
    echo ""
    echo -e "${DIM}Setting JWT_JWKS_FILE=${JWT_JWKS_FILE}${NC}"
    set_service_var JWT_JWKS_FILE "$JWT_JWKS_FILE"
elif [[ -n "$AUTH_REQUIRES_JWT" ]]; then
    # Not just "traffic will 401": AgentOS(authorization=True) raises on import
    # without a key source, so the container exits before uvicorn binds. With
    # railway.json's healthcheck on /health that shows up as a failed deploy,
    # which is the honest reading — say so, or the logs look like a mystery.
    echo ""
    echo -e "${DIM}Deploying without JWT auth config. AgentOS refuses to construct without a key,${NC}"
    echo -e "${DIM}so the container exits on boot and this deploy will fail its healthcheck. Add${NC}"
    echo -e "${DIM}JWT_VERIFICATION_KEY or JWT_JWKS_FILE to ${ENV_FILE:-.env.production}, then run${NC}"
    echo -e "${DIM}./scripts/railway/env-sync.sh to bring it up.${NC}"
fi

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Deploying application${NC}"
echo ""
railway up --service agent-os -d

echo ""
echo -e "${BOLD}Done.${NC} The app is building — give it a few minutes."
[[ -n "$APP_URL" ]] && echo -e "${DIM}URL:            ${APP_URL}${NC}"
echo -e "${DIM}Logs:           railway logs --service agent-os${NC}"
echo -e "${DIM}Sync env vars:  ./scripts/railway/env-sync.sh${NC}"
[[ -n "$APP_URL" ]] && echo -e "${DIM}Connect apps:   uvx agno connect --url ${APP_URL}${NC}"
if [[ -n "$APP_URL" && -n "$MCP_SECRET_ON_RAILWAY" ]]; then
    echo -e "${DIM}Chat apps:      add ${APP_URL}/mcp as a custom connector in claude.ai / ChatGPT${NC}"
    echo -e "${DIM}                (leave the optional OAuth client ID/secret fields empty).${NC}"
    echo -e "${DIM}                Then click Connect and approve the consent page with this secret:${NC}"
    echo -e "${BOLD}                ${MCP_CONNECT_SECRET}${NC}"
fi
# Last word, because it's the one thing about this deploy the operator must not
# forget: the URL above answers anyone who has it.
if [[ "$RUNTIME_ENV" == "dev" ]]; then
    echo ""
    echo -e "${RED}${BOLD}This deploy runs unauthenticated (RUNTIME_ENV=dev).${NC} Tear it down when you're done,"
    echo -e "or drop RUNTIME_ENV from ${ENV_FILE:-your env file}, add a JWT key, and re-sync."
fi
echo ""
