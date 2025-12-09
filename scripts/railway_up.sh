#!/bin/bash

# Use this script to deploy Agent OS on Railway
# Prerequisites:
# - Railway CLI installed
# - Railway account logged in via `railway login`

set -e  # Exit on any error

echo -e "🚂 Starting Railway deployment...\n"

# Load .env file if it exists
if [ -f .env ]; then
    echo -e "📄 .env file found...\n"
    set -a #run export command for all variables in .env file
    source .env
    set +a
fi

# Initialize a new project on Railway (uncomment if needed)
railway init -n "agentos-railway"

echo -e "📦 Deploying PgVector database...\n"
railway deploy -t 3jJFCA

echo -e "⏳ Waiting 10 seconds for database to be created...\n"
sleep 10

echo -e "🔧 Creating application service with environment variables...\n"
railway add --service agent_os \
  --variables "DB_DRIVER=postgresql+psycopg" \
  --variables 'DB_USER=${{pgvector.PGUSER}}' \
  --variables 'DB_PASS=${{pgvector.PGPASSWORD}}' \
  --variables 'DB_HOST=${{pgvector.PGHOST}}' \
  --variables 'DB_PORT=${{pgvector.PGPORT}}' \
  --variables 'DB_DATABASE=${{pgvector.PGDATABASE}}' \
  --variables "OPENAI_API_KEY=${OPENAI_API_KEY}" \
  --variables "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
  --variables "PARALLEL_API_KEY=${PARALLEL_API_KEY}"

echo -e "🚀 Deploying application...\n"
railway up --service agent_os -d

echo -e "🔗 Creating domain...\n"
railway domain --service agent_os

echo -e "Note: It may take up to 5 minutes for the domain to reach ready state while the application is deploying.\n"

echo -e "✅ Deployment complete!\n"
echo -e "💡 Tip: Run 'railway logs --service agent_os' to view your application logs.\n"
