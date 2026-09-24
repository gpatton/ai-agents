
# AgentForge

AgentForge is a locally developed AI-agent application with a FastAPI backend and a React dashboard. It supports authenticated conversations, streaming agent responses, tool-execution details, document search, and persistent conversation history.

## Technology stack

- **Backend:** Python 3.12, FastAPI, LangGraph, and MCP
- **Frontend:** React, Vite, and Clerk authentication
- **Database:** PostgreSQL for application data and conversation checkpoints
- **Document search:** Chroma and OpenAI embeddings
- **Local deployment:** Docker Compose
- **Testing:** pytest and GitHub Actions

## Project structure

```text
ai-agents/
├── app/                 # Backend API, agent, tools, and repositories
├── alembic/             # Database migrations
├── data/                # Source documents for document search
├── frontend/            # React dashboard
├── tests/               # Automated backend tests
├── .env.example         # Backend environment-variable template
├── compose.yaml         # Docker Compose services
├── Dockerfile           # Backend container image
└── requirements.txt     # Python dependencies
```

## Prerequisites

For the Docker-based backend and locally running dashboard, install:

- Docker with Docker Compose
- Node.js and npm
- Git

You will also need an OpenAI API key and a configured Clerk application.

Python 3.12 is required if you want to run the backend or its tests directly outside Docker.

## 1. Configure the backend

Clone the repository and open the project directory:

```bash
git clone YOUR_REPOSITORY_URL
cd ai-agents
```

Create a local environment file from the template:

```bash
cp .env.example .env
```

Edit `.env` and configure the following values:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API access |
| `APP_NAME` | Application name |
| `MODEL_NAME` | Model used by AgentForge |
| `CLERK_ISSUER` | Issuer URL for your Clerk application |
| `CLERK_ALLOWED_AUTHORIZED_PARTIES` | Additional permitted Clerk authorized-party URLs, if needed |
| `POSTGRES_PASSWORD` | Password for the local PostgreSQL service |
| `DATABASE_URL` | Database connection URL for running the backend outside Docker |
| `CHROMA_DIR` | Chroma persistence directory |
| `MCP_SERVER_PATH` | Path to the MCP server |
| `CORS_ALLOWED_ORIGINS` | Additional dashboard origins permitted to call the API |

Do not commit `.env`, API keys, database passwords, or authentication tokens.

**Database connection:** The `.env.example` database URL uses `localhost:55433` for a backend running directly on your computer. When AgentForge runs through Docker Compose, `compose.yaml` supplies a database URL that connects to the `postgres` service inside Docker.

## 2. Start the backend

From the project root:

```bash
docker compose up -d --build --wait
```

This starts PostgreSQL and AgentForge. The application checks its document index and runs database migrations during startup.

Check that the services are running:

```bash
docker compose ps
```

Check API readiness:

```bash
curl http://127.0.0.1:8000/ready
```

The expected response is:

```json
{"status":"ready","service":"AgentForge"}
```

The API documentation is available locally at:

http://127.0.0.1:8000/docs

To stop the services without deleting their data volumes:

```bash
docker compose stop
```

**Data safety:** PostgreSQL and Chroma use persistent Docker volumes. Do not use `docker compose down -v` unless you intentionally want to delete those volumes and their data.

## 3. Configure and start the dashboard

Open a second terminal:

```bash
cd ai-agents/frontend
npm ci
```

Configure the frontend environment in `frontend/.env.local`. The dashboard uses these variables:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

Use the publishable key from your Clerk application. Do not put Clerk secret keys or your OpenAI API key in frontend environment variables.

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite in your browser, then sign in through Clerk.

The dashboard provides a place to send requests, view responses, and inspect tool-execution details.

## 4. Run backend tests

Create and activate a Python 3.12 virtual environment if you do not already have one:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Configure the environment variables required by the tests, then run:

```bash
python -m pytest -q
```

The GitHub Actions workflow in `.github/workflows/ci.yml` also runs the Python tests on pushes and pull requests targeting `main`.

## 5. Check the frontend

From `frontend/`:

```bash
npm run lint
npm run build
```

The build command produces the frontend’s production build. The local development server is started with `npm run dev`.

## 6. View logs

To follow the backend container’s console logs:

```bash
docker compose logs -f agentforge
```

To stop following the logs, press `Ctrl+C`.

AgentForge’s Docker console logs are configured for rotation. The application also writes a log file inside its container at `/app/logs/agentforge.log`.

Avoid sharing logs publicly without checking them for sensitive information.

## 7. Troubleshooting

**The API is not ready:** Check service status and backend logs:

```bash
docker compose ps
docker compose logs --tail=100 agentforge
```

**The dashboard cannot reach the API:** Confirm that `/ready` responds and that `VITE_API_URL` points to the correct backend address.

**Authentication fails:** Check the Clerk issuer, frontend publishable key, and authorized-party configuration. Do not paste session tokens into bug reports.

**Document search fails:** Check the backend logs and confirm that the configured Chroma directory is writable. The Docker setup uses a persistent Chroma volume.

## Development status

AgentForge is under active development. The current setup is intended for local development and testing; production deployment configuration and documentation will be added separately.
