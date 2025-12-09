@echo off
REM ##########################################################################
REM Format the workspace using ruff
REM Usage: format.bat
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
echo Formatting workspace...
echo ========================================
echo.

echo ========================================
echo Running: ruff format %REPO_ROOT%
echo ========================================
ruff format "%REPO_ROOT%"
echo.

echo ========================================
echo Running: ruff check --select I --fix %REPO_ROOT%
echo ========================================
ruff check --select I --fix "%REPO_ROOT%"
echo.

echo Done!
echo.

pause