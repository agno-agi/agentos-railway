#!/bin/bash

############################################################################
#
#    Agno Workspace Validator
#
#    Usage: ./scripts/validate.sh
#
############################################################################

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${CURR_DIR}")"

# Colors
ORANGE='\033[38;5;208m'
RED='\033[31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo -e "${RED}Warning:${NC} no virtualenv active. Run: ${BOLD}source .venv/bin/activate${NC}"
  echo ""
fi

echo ""
echo -e "${ORANGE}▸${NC} ${BOLD}Validating workspace${NC}"
echo ""

failed=0

echo -e "${DIM}> ruff format --check ${REPO_ROOT}${NC}"
if ! ruff format --check "${REPO_ROOT}"; then
  echo -e "${RED}Fix with:${NC} ${BOLD}./scripts/format.sh${NC}"
  failed=1
fi

echo ""
echo -e "${DIM}> ruff check ${REPO_ROOT}${NC}"
if ! ruff check "${REPO_ROOT}"; then
  failed=1
fi

echo ""
echo -e "${DIM}> mypy ${REPO_ROOT} --config-file ${REPO_ROOT}/pyproject.toml${NC}"
if ! mypy "${REPO_ROOT}" --config-file "${REPO_ROOT}/pyproject.toml"; then
  failed=1
fi

echo ""
if [[ $failed -eq 0 ]]; then
  echo -e "${BOLD}Done.${NC}"
else
  echo -e "${RED}${BOLD}Failed.${NC}"
fi
echo ""

exit "$failed"
