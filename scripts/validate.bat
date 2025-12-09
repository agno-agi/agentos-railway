@echo off
REM ##########################################################################
REM Validate workspace using ruff and mypy
REM   1. Lint using ruff
REM   2. Type check using mypy
REM Usage: validate.bat
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
echo Validating workspace...
echo ========================================
echo.

echo ========================================
echo Running: ruff check %REPO_ROOT%
echo ========================================
ruff check "%REPO_ROOT%"
echo.

echo ========================================
echo Running: mypy %REPO_ROOT% --config-file %REPO_ROOT%\pyproject.toml
echo ========================================
mypy "%REPO_ROOT%" --config-file "%REPO_ROOT%\pyproject.toml"
echo.

echo Done!
echo.

pause