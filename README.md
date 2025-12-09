# AgentOS on Railway

This repo contains code for running a production-grade multi-agent system on Railway. It's powered by the AgentOS: a high-performance runtime for serving agents, multi-agent teams and agentic workflows.

This repo gives you:
- **AgentOS runtime:** for serving agents, multi-agent teams and agentic workflows.
- **PostgreSQL database:** for storing agent sessions, knowledge, and memories.
- A set of **pre-built agents, teams and workflows** to use as a starting point.

For more details, checkout [Agno](https://agno.link/gh) and give it a ⭐️

## Get Started

Follow these steps to run your AgentOS:

### Clone the repo

```sh
git clone https://github.com/agno-agi/agentos-railway.git
cd agentos-railway
```

### Configure API keys

We'll use OpenAI, Anthropic and Parallel Search services. Please export the following environment variables:

```sh
export OPENAI_API_KEY="YOUR_API_KEY_HERE"
export ANTHROPIC_API_KEY="YOUR_API_KEY_HERE"
export PARALLEL_API_KEY="YOUR_API_KEY_HERE"
```

> [!TIP]
> You can copy the `example.env` file and rename it to `.env` to get started.

### Install Docker

We'll use docker to run the application locally and deploy it to Railway. Please install [Docker Desktop](https://www.docker.com/products/docker-desktop) if needed.

## Run AgentOS Locally

Run the application using docker compose:

```sh
docker compose up --build -d
```

This command builds the Docker image and starts the application:

- The **AgentOS server**, running on [http://localhost:8000](http://localhost:8000).
- The **PostgreSQL database** for storing agent sessions, knowledge, and memories, accessible on `localhost:5432`.

Once started, you can:

- View the AgentOS runtime at [http://localhost:8000/docs](http://localhost:8000/docs).

### Connect the AgentOS UI to the AgentOS server

- Open the [AgentOS UI](https://os.agno.com/?utm_source=github&utm_medium=example-repo&utm_campaign=ab-examples-railway&utm_content=railway-example&utm_term=railway)
- Login and add `http://localhost:8000` as a new AgentOS. You can call it `Local AgentOS` (or any name you prefer).

### Load Knowledge Base for the Agno Knowledge Agent

The Agno Knowledge Agent is a great example of building a knowledge agent using Agentic RAG. It loads the Agno documentation into pgvector and answers questions from the docs.

To populate the knowledge base, run the following command:

```sh
docker exec -it agentos-railway-agent-os-1 python -m agents.agno_knowledge_agent
```

### Stop the application

When you're done, stop the application using:

```sh
docker compose down
```

## Deploy AgentOS to Railway

To deploy the application to Railway, run the following commands:

1. Install Railway CLI:

```sh
brew install railway
```

More information on how to install Railway CLI can be found [here](https://docs.railway.com/guides/cli).

2. Login to Railway:

```sh
railway login
```

3. Deploy the application:

```sh
./scripts/railway_up.sh
```

This command will:

- Create a new Railway project.
- Deploy a PgVector database service to your Railway project.
- Build and deploy the docker image to your Railway project.
- Set environment variables in your AgentOS service.
- Create a new domain for your AgentOS service.

### Updating the application

To update the application, run the following command:

```sh
railway up --service agent_os -d
```

This rebuilds and redeploys the Docker image to your Railway service.

### Deleting the application

To delete the application, run the following command:

```sh
railway down --service agent_os
railway down --service pgvector
```

Careful: This command will delete the AgentOS and PgVector database services from your Railway project.

### Connecting the AgnoUI to the AgentOS server

To connect the AgentOS UI to the AgentOS server:

- Open the [AgentOS UI](https://os.agno.com/?utm_source=github&utm_medium=example-repo&utm_campaign=ab-examples-railway&utm_content=railway-example&utm_term=railway)
- Create a new AgentOS by clicking on the `+` button in the top left corner.
- Enter the AgentOS URL and click on the `Connect` button.
- You can add a local endpoint from your dev setup. To add the railway endpoint, you will be provided with a coupon code during the workshop.

## Development Setup

Follow these steps to setup your local development environment:

### Install `uv`

We use `uv` for python environment and package management. Install it by following the the [`uv` documentation](https://docs.astral.sh/uv/#getting-started) or use the command below for unix-like systems:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create Virtual Environment & Install Dependencies

Run the `dev_setup.sh` script. This will create a virtual environment and install project dependencies:

```sh
./scripts/dev_setup.sh
```

### Activate Virtual Environment

Activate the created virtual environment:

```sh
source .venv/bin/activate
```

(On Windows, the command might differ, e.g., `.venv\Scripts\activate`)

## Managing Python Dependencies

If you need to add or update python dependencies:

### Modify pyproject.toml

Add or update your desired Python package dependencies in the `[dependencies]` section of the `pyproject.toml` file.

### Generate requirements.txt

The `requirements.txt` file is used to build the application image. After modifying `pyproject.toml`, regenerate `requirements.txt` using:

```sh
./scripts/generate_requirements.sh
```

To upgrade all existing dependencies to their latest compatible versions, run:

```sh
./scripts/generate_requirements.sh upgrade
```

### Rebuild Docker Images

Rebuild your Docker images to include the updated dependencies:

```sh
docker compose up -d --build
```

## Community & Support

Need help, have a question, or want to connect with the community?

- 📚 **[Read the Agno Docs](https://docs.agno.com/?utm_source=github&utm_medium=example-repo&utm_campaign=ab-examples-railway&utm_content=railway-example&utm_term=railway)** for more in-depth information.
- 💬 **Chat with us on [Discord](https://agno.link/discord)** for live discussions.
- ❓ **Ask a question on [Discourse](https://agno.link/community)** for community support.
- 🐛 **[Report an Issue](https://github.com/agno-agi/agno/issues)** on GitHub if you find a bug or have a feature request.
