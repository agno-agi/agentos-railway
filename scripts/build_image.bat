@echo off
REM ##########################################################################
REM Script to build the Docker image using Docker Buildx.
REM
REM Instructions:
REM 1. Set the IMAGE_NAME and IMAGE_TAG variables to the desired values.
REM 2. Ensure Docker Buildx is installed and configured.
REM 3. Run 'docker buildx create --use' before executing this script.
REM
REM This script builds a multi-platform Docker image for linux/amd64 and linux/arm64.
REM The image is tagged and pushed to the specified repository.
REM ##########################################################################

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "CURR_DIR=%~dp0"
REM Remove trailing backslash
set "CURR_DIR=%CURR_DIR:~0,-1%"

REM Get the workspace root (parent directory)
for %%I in ("%CURR_DIR%") do set "WS_ROOT=%%~dpI"
set "WS_ROOT=%WS_ROOT:~0,-1%"

set "DOCKER_FILE=Dockerfile"
set "IMAGE_NAME=agentos-railway"
set "IMAGE_TAG=latest"

echo Running: docker buildx build --platform=linux/amd64,linux/arm64 -t %IMAGE_NAME%:%IMAGE_TAG% -f %DOCKER_FILE% %WS_ROOT% --push
docker buildx build --platform=linux/amd64,linux/arm64 -t %IMAGE_NAME%:%IMAGE_TAG% -f %DOCKER_FILE% "%WS_ROOT%" --push

if %errorlevel% neq 0 (
    echo.
    echo Error: Docker build failed with exit code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo Build completed successfully!
echo.

pause
