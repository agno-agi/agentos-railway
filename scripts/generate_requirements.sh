#!/bin/bash

############################################################################
#
#    Agno Requirements Generator
#
#    Usage:
#      ./scripts/generate_requirements.sh           # Generate
#      ./scripts/generate_requirements.sh upgrade   # Generate with upgrade
#      ./scripts/generate_requirements.sh <pkg>...  # Refresh only these pins
#
############################################################################

set -e

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${CURR_DIR}")"

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "    ${ORANGE}▸${NC} ${BOLD}Generating requirements.txt${NC}"
echo ""

if [[ "$1" = "upgrade" ]]; then
    echo -e "    ${DIM}Mode: upgrade${NC}"
    echo -e "    ${DIM}> uv pip compile pyproject.toml --no-cache --upgrade -o requirements.txt${NC}"
    echo ""
    UV_CUSTOM_COMPILE_COMMAND="./scripts/generate_requirements.sh upgrade" \
        uv pip compile "${REPO_ROOT}/pyproject.toml" --no-cache --upgrade -o "${REPO_ROOT}/requirements.txt"
elif [[ $# -gt 0 ]]; then
    # Refresh only the named packages; every other pin stays put. Needed when a pin
    # is held by a floor rather than the pyproject pin (agno floors agnoctl at the
    # previous published release, so a plain regen never moves it).
    UPGRADE_FLAGS=()
    for pkg in "$@"; do
        UPGRADE_FLAGS+=("--upgrade-package" "$pkg")
    done
    echo -e "    ${DIM}Mode: refresh ($*)${NC}"
    echo -e "    ${DIM}> uv pip compile pyproject.toml --no-cache ${UPGRADE_FLAGS[*]} -o requirements.txt${NC}"
    echo ""
    UV_CUSTOM_COMPILE_COMMAND="./scripts/generate_requirements.sh $*" \
        uv pip compile "${REPO_ROOT}/pyproject.toml" --no-cache "${UPGRADE_FLAGS[@]}" -o "${REPO_ROOT}/requirements.txt"
else
    echo -e "    ${DIM}Mode: standard${NC}"
    echo -e "    ${DIM}> uv pip compile pyproject.toml --no-cache -o requirements.txt${NC}"
    echo ""
    UV_CUSTOM_COMPILE_COMMAND="./scripts/generate_requirements.sh" \
        uv pip compile "${REPO_ROOT}/pyproject.toml" --no-cache -o "${REPO_ROOT}/requirements.txt"
fi

echo ""
echo -e "    ${BOLD}Done.${NC}"
echo ""