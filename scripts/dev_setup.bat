@echo off
REM ##########################################################################
REM Development Setup
REM - This script creates a virtual environment and installs libraries in editable mode.
REM - Please install uv before running this script. 
REM - uv can be installed using the following command on Windows:
REM - powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
REM - Please deactivate the existing virtual environment before running.
REM Usage: dev_setup.bat
REM ##########################################################################

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "CURR_DIR=%~dp0"
REM Remove trailing backslash
set "CURR_DIR=%CURR_DIR:~0,-1%"

REM Get the repository root (parent directory)
for %%I in ("%CURR_DIR%") do set "REPO_ROOT=%%~dpI"
set "REPO_ROOT=%REPO_ROOT:~0,-1%"

set "VENV_DIR=%REPO_ROOT%\.venv"

echo ========================================
echo Development setup...
echo ========================================
echo.

echo ========================================
echo Removing virtual env
echo ========================================
echo rm -rf %VENV_DIR%
if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%"
)
echo.

echo ========================================
echo Creating virtual env
echo ========================================
echo VIRTUAL_ENV=%VENV_DIR% uv venv --python 3.12
set "VIRTUAL_ENV=%VENV_DIR%"
uv venv --python 3.12
echo.

echo ========================================
echo Installing requirements
echo ========================================
echo VIRTUAL_ENV=%VENV_DIR% uv pip install -r %REPO_ROOT%\requirements.txt
set "VIRTUAL_ENV=%VENV_DIR%"
uv pip install -r "%REPO_ROOT%\requirements.txt"
echo.

echo ========================================
echo Installing workspace in editable mode with dev dependencies
echo ========================================
echo VIRTUAL_ENV=%VENV_DIR% uv pip install -e %REPO_ROOT%[dev]
set "VIRTUAL_ENV=%VENV_DIR%"
uv pip install -e "%REPO_ROOT%[dev]"
echo.

echo ========================================
echo Development setup complete
echo ========================================
echo Activate venv using: .venv\Scripts\activate
echo.

pause