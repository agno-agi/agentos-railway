@echo off
REM ##########################################################################
REM Generate requirements.txt from pyproject.toml
REM Usage:
REM generate_requirements.bat: Generate requirements.txt
REM generate_requirements.bat upgrade: Upgrade requirements.txt
REM ##########################################################################

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "CURR_DIR=%~dp0"
REM Remove trailing backslash
set "CURR_DIR=%CURR_DIR:~0,-1%"

REM Get the repository root (parent directory)
for %%I in ("%CURR_DIR%") do set "REPO_ROOT=%%~dpI"
set "REPO_ROOT=%REPO_ROOT:~0,-1%"

echo ========================================
echo Generating requirements.txt...
echo ========================================
echo.

if "%1"=="upgrade" (
    echo ========================================
    echo Generating requirements.txt with upgrade
    echo ========================================
    set "UV_CUSTOM_COMPILE_COMMAND=.\scripts\generate_requirements.bat upgrade"
    uv pip compile "%REPO_ROOT%\pyproject.toml" --no-cache --upgrade -o "%REPO_ROOT%\requirements.txt"
) else (
    echo ========================================
    echo Generating requirements.txt
    echo ========================================
    set "UV_CUSTOM_COMPILE_COMMAND=.\scripts\generate_requirements.bat"
    uv pip compile "%REPO_ROOT%\pyproject.toml" --no-cache -o "%REPO_ROOT%\requirements.txt"
)

echo.
echo Done!
echo.

pause