#!/bin/bash

############################################################################
#
#    Agno Railway Teardown
#
#    Usage:
#      ./scripts/railway/down.sh          # asks before destroying
#      ./scripts/railway/down.sh --yes    # no prompt (CI / automation)
#
#    Deletes the linked Railway project — the agent-os service, the
#    pgvector database, and its volume. All data in the database is
#    deleted. Run from the repo root. Verify afterwards with
#    `railway list`.
#
#    Once the project is confirmed gone, comments the two settings that
#    died with it out of .env.production / .env — the Railway-minted
#    AGENTOS_URL and JWT_VERIFICATION_KEY — so the next up.sh derives a
#    fresh domain and re-runs its guided key step.
#
############################################################################

set -e

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
RED='\033[31m'
NC='\033[0m'

# Comment out a KEY= block, PEM continuation lines included, and stamp the
# reason above it. Commenting only the first line of a multi-line value is worse
# than leaving it: up.sh's env parser skips the commented `KEY="-----BEGIN...`
# line and then reads the next base64 line as a key name of its own. Rewrites
# through the original file (not `mv`) so it keeps its inode and permissions.
# Returns 1 when there was no active block to comment.
comment_out_env_block() {
    local key="$1" file="$2" tmp line commenting=0 hit=0 value_part reason
    shift 2
    [[ -f "$file" ]] || return 1
    grep -qE "^[[:space:]]*${key}=" "$file" || return 1

    tmp="$(mktemp)"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$commenting" == 1 ]]; then
            printf '# %s\n' "$line" >> "$tmp"
            [[ "$line" == *"-----END"* ]] && commenting=0
            continue
        fi
        if [[ "$line" =~ ^[[:space:]]*${key}= ]]; then
            hit=1
            for reason in "$@"; do
                printf '# %s\n' "$reason" >> "$tmp"
            done
            printf '# %s\n' "$line" >> "$tmp"
            value_part="${line#*=}"
            if [[ "$value_part" == *"-----BEGIN"* && "$value_part" != *"-----END"* ]]; then
                commenting=1
            fi
            continue
        fi
        printf '%s\n' "$line" >> "$tmp"
    done < "$file"

    cat "$tmp" > "$file"
    rm -f "$tmp"
    [[ "$hit" == 1 ]]
}

# Preflight
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Install: https://docs.railway.com/cli#installing-the-cli"
    exit 1
fi

if ! railway whoami &> /dev/null; then
    echo "Not logged in to Railway. Run: railway login"
    exit 1
fi

if ! railway status &> /dev/null; then
    echo "Not linked to a Railway project — nothing to tear down."
    echo "Run this from the directory ./scripts/railway/up.sh deployed from, or check: railway list"
    exit 1
fi

# Identify the linked project. `railway status --json` returns the project
# object, so its first "id"/"name" are the project's own (service and
# environment ids are nested deeper). Fragments are split on ',' and '{'
# first because a greedy sed over one long JSON line would match the LAST
# occurrence, not the first.
STATUS_JSON="$(railway status --json 2> /dev/null)"
PROJECT_ID="$(tr ',{' '\n' <<< "$STATUS_JSON" | sed -nE 's/.*"id": *"([^"]+)".*/\1/p' | head -1)"
PROJECT_NAME="$(tr ',{' '\n' <<< "$STATUS_JSON" | sed -nE 's/.*"name": *"([^"]+)".*/\1/p' | head -1)"

if [[ -z "$PROJECT_ID" || -z "$PROJECT_NAME" ]]; then
    echo "Couldn't read the linked project from 'railway status --json'."
    echo "Delete it manually with 'railway delete' or from the Railway dashboard."
    exit 1
fi

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Railway Teardown${NC}"
echo ""
echo -e "This deletes the Railway project:"
echo -e "  - project   ${PROJECT_NAME}  ${DIM}(${PROJECT_ID})${NC}"
echo -e "  - services  agent-os + pgvector  ${RED}(all data deleted)${NC}"
echo ""

if [[ "$1" != "--yes" ]]; then
    printf "Type the project name (%s) to confirm: " "$PROJECT_NAME"
    IFS= read -r CONFIRM
    if [[ "$CONFIRM" != "$PROJECT_NAME" ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo -e "${DIM}> railway delete --project ${PROJECT_ID} --yes${NC}"
railway delete --project "$PROJECT_ID" --yes \
    || echo -e "${DIM}Delete returned non-zero — verifying below${NC}"

# The project only counts as gone when Railway no longer lists it. `railway
# list` also fails on an expired token or a network blip — treating that as
# "gone" would unlink the directory while the project (and its database)
# is still alive and billing.
if ! LIST_JSON="$(railway list --json 2>&1)"; then
    echo ""
    echo -e "${RED}${BOLD}Couldn't verify the project is gone${NC} — railway list failed with:"
    echo -e "${DIM}${LIST_JSON}${NC}"
    echo "The directory stays linked so you can retry. Check: railway list"
    exit 1
fi

if grep -qF "$PROJECT_ID" <<< "$LIST_JSON"; then
    echo ""
    echo -e "${RED}${BOLD}Teardown incomplete${NC} — the project is still listed. Retry, or if your"
    echo -e "account has 2FA enabled, delete needs a code in non-interactive mode:"
    echo -e "${DIM}  railway delete --project ${PROJECT_ID} --yes --2fa-code <code>${NC}"
    exit 1
fi

# A Railway-minted domain dies with the project. Comment it out of the env
# file(s) so a future up.sh derives the fresh domain instead of pinning the
# dead one; custom domains are left alone.
#
# JWT_VERIFICATION_KEY goes with it. It belongs to the os.agno.com OS connection
# that pointed at the domain just deleted, and up.sh's guided key step is gated
# on the variable being absent — left in place it silently skips, and the next
# deploy comes up verifying tokens against a connection nobody is minting them
# from. Commenting it costs one paste; leaving it costs a platform that refuses
# every request.
for f in .env.production .env; do
    [[ -f "$f" ]] || continue
    if grep -qE '^AGENTOS_URL=.*\.up\.railway\.app/?$' "$f"; then
        sed -i.bak -E 's|^(AGENTOS_URL=.*\.up\.railway\.app/?)$|# \1|' "$f" && rm -f "$f.bak"
        echo -e "${DIM}Commented out the stale AGENTOS_URL in ${f}${NC}"
    fi
    if comment_out_env_block JWT_VERIFICATION_KEY "$f" \
        "Commented out by scripts/railway/down.sh — minted at os.agno.com for the" \
        "deployment just deleted. up.sh will walk you through a fresh key; uncomment" \
        "this instead if you point the same OS connection at the new domain."; then
        echo -e "${DIM}Commented out the stale JWT_VERIFICATION_KEY in ${f}${NC}"
    fi
done

# Only unlink once the project is confirmed gone — unlinking after a failed
# delete would leave the resources running with no local record of them.
railway unlink --yes &> /dev/null || true

echo ""
echo -e "${BOLD}Done.${NC} Project confirmed gone and directory unlinked. Verify anytime with: railway list"
echo ""
