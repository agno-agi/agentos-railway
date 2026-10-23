#!/usr/bin/env bash

############################################################################
#
#    Agno Virtual Environment Setup
#
#    Usage: ./scripts/venv_setup.sh
#
############################################################################

set -euo pipefail

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${CURR_DIR}")"
VENV_DIR="${REPO_ROOT}/.venv"

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
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
echo -e "    ${DIM}Virtual Environment Setup${NC}"
echo ""

# Preflight
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "    Deactivate your current venv first."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "    uv not found. Install: https://docs.astral.sh/uv/"
    exit 1
fi

# Setup
if [[ -x "${VENV_DIR}/bin/python" ]]; then
    echo -e "    ${DIM}Using existing environment: ${VENV_DIR}${NC}"
else
    echo -e "    ${DIM}Creating Python 3.14 venv...${NC}"
    echo -e "    ${DIM}> uv venv ${VENV_DIR} --python 3.14${NC}"
    uv venv "${VENV_DIR}" --python 3.14 --quiet
fi

echo ""
echo -e "    ${DIM}Installing requirements...${NC}"
echo -e "    ${DIM}> uv pip install --python ${VENV_DIR}/bin/python -r requirements.txt${NC}"
uv pip install --python "${VENV_DIR}/bin/python" -r "${REPO_ROOT}/requirements.txt" --quiet

echo ""
echo -e "    ${DIM}Installing project in editable mode with dev dependencies...${NC}"
echo -e "    ${DIM}> uv pip install --python ${VENV_DIR}/bin/python -c requirements.txt -e .[dev]${NC}"
uv pip install --python "${VENV_DIR}/bin/python" -c "${REPO_ROOT}/requirements.txt" -e "${REPO_ROOT}[dev]" --quiet

# Copy activation command to clipboard
ACTIVATE_CMD="source .venv/bin/activate"
CLIPBOARD_MSG=""
if command -v pbcopy &> /dev/null; then
    if printf '%s' "${ACTIVATE_CMD}" | pbcopy; then
        CLIPBOARD_MSG="(Copied to clipboard)"
    fi
elif command -v xclip &> /dev/null; then
    if printf '%s' "${ACTIVATE_CMD}" | xclip -selection clipboard; then
        CLIPBOARD_MSG="(Copied to clipboard)"
    fi
fi

echo ""
echo -e "    ${BOLD}Done.${NC}"
echo ""
echo -e "    ${DIM}Activate:${NC}  ${ACTIVATE_CMD} ${DIM}${CLIPBOARD_MSG}${NC}"
echo ""
