@echo off
REM ##########################################################################
REM Use this script to deploy Agent OS on Railway
REM Prerequisites:
REM - Railway CLI installed
REM - Railway account logged in via `railway login`
REM ##########################################################################

setlocal

echo ========================================
echo 🚂 Starting Railway deployment...
echo ========================================
echo.

echo ========================================
echo 📋 Initializing Railway project...
echo ========================================
cmd /c railway init -n "agentos-railway"
echo.

echo ========================================
echo 📦 Deploying PgVector database...
echo ========================================
cmd /c railway deploy -t 3jJFCA
echo.

echo ========================================
echo ⏳ Waiting 10 seconds for database to be created...
echo ========================================
timeout /t 10 /nobreak >nul
echo.

echo ========================================
echo 🔧 Creating application service with environment variables...
echo ========================================
cmd /c railway add --service agent_os ^
  --variables "DB_DRIVER=postgresql+psycopg" ^
  --variables "DB_USER=${{pgvector.PGUSER}}" ^
  --variables "DB_PASS=${{pgvector.PGPASSWORD}}" ^
  --variables "DB_HOST=${{pgvector.PGHOST}}" ^
  --variables "DB_PORT=${{pgvector.PGPORT}}" ^
  --variables "DB_DATABASE=${{pgvector.PGDATABASE}}" ^
  --variables "OPENAI_API_KEY=%OPENAI_API_KEY%" ^
  --variables "ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%" ^
  --variables "PARALLEL_API_KEY=%PARALLEL_API_KEY%"
echo.

echo ========================================
echo 🚀 Deploying application...
echo ========================================
cmd /c railway up --service agent_os -d
echo.

echo ========================================
echo 🔗 Creating domain...
echo ========================================
cmd /c railway domain --service agent_os
echo.

echo ========================================
echo ✅ Deployment complete!
echo ========================================
echo.
echo 📝 Note: It may take up to 5 minutes for the domain to reach ready state
echo     while the application is deploying.
echo.
echo 💡 Tip: Run 'railway logs --service agent_os' to view your application logs.
echo.

pause
endlocal
