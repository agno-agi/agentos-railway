#!/bin/bash

############################################################################
#
#    Agno Docker Image Builder
#
#    Usage:
#      ./scripts/build_image.sh
#      IMAGE_NAME=you/agentos IMAGE_TAG=3.0.0 ./scripts/build_image.sh
#
#    Prerequisites:
#      - Docker Buildx installed
#      - Run 'docker buildx create --use' first
#      - 'docker login' for the registry IMAGE_NAME points at — this build pushes
#
############################################################################

set -e

CURR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_ROOT="$(dirname "${CURR_DIR}")"
DOCKER_FILE="${OS_ROOT}/Dockerfile"
IMAGE_NAME="${IMAGE_NAME:-agnohq/agentos}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors
ORANGE='\033[38;5;208m'
RED='\033[31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Fail before the build rather than at the push. compose.yaml defaults IMAGE_NAME to a
# bare "agentos", so an export meant for local dev lands here as an unpushable target.
if [[ "${IMAGE_NAME}" != */* ]]; then
    echo ""
    echo -e "    ${RED}${BOLD}IMAGE_NAME has no registry namespace:${NC} ${IMAGE_NAME}"
    echo -e "    ${DIM}Pushing there means docker.io/library/${IMAGE_NAME}, which is not writable.${NC}"
    echo -e "    ${DIM}Set one: IMAGE_NAME=you/${IMAGE_NAME} ./scripts/build_image.sh${NC}"
    echo ""
    exit 1
fi

echo ""
echo -e "    ${ORANGE}▸${NC} ${BOLD}Building Docker image${NC}"
echo -e "    ${DIM}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo -e "    ${DIM}Platforms: linux/amd64, linux/arm64${NC}"
echo ""

echo -e "    ${DIM}> docker buildx build --platform=linux/amd64,linux/arm64 -t ${IMAGE_NAME}:${IMAGE_TAG} -f ${DOCKER_FILE} ${OS_ROOT} --push${NC}"
docker buildx build --platform=linux/amd64,linux/arm64 -t "${IMAGE_NAME}:${IMAGE_TAG}" -f "${DOCKER_FILE}" "${OS_ROOT}" --push

echo ""
echo -e "    ${BOLD}Done.${NC}"
echo ""