# AgentForge

AgentForge is a locally developed AI-agent application with a FastAPI backend and a React dashboard. It supports authenticated conversations, streaming agent responses, tool-execution details, document search, evaluation reports, and persistent conversation history.

## Technology stack

- **Backend:** Python 3.12, FastAPI, LangGraph, and MCP
- **Frontend:** React, Vite, and Clerk authentication
- **Database:** PostgreSQL for application data and conversation checkpoints
- **Document search:** Chroma and OpenAI embeddings
- **Local deployment:** Docker Compose and Kubernetes with kind
- **Testing:** pytest and GitHub Actions

## Project structure

```text
ai-agents/
├── app/                 # Backend API, agent, tools, and repositories
├── alembic/             # Database migrations
├── data/                # Source documents for document search
├── frontend/            # React dashboard and frontend container configuration
├── k8s/                 # Kubernetes deployment, service, and storage manifests
├── reports/             # Locally generated evaluation reports
├── scripts/             # Deployment scripts
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

For the Kubernetes workflow, also install:

- kind
- kubectl
- Python available as `python`, for the deployment script

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

The dashboard provides a place to send requests, view responses, inspect tool-execution details, and view available evaluation reports.

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

## 8. Local Kubernetes deployment (kind)

AgentForge also runs in a local kind cluster named `agentforge`, using the `agentforge` namespace.

This section assumes the cluster, configuration, secrets, storage claims, and deployments are already installed. It describes operating and updating the existing setup.

### Check deployment status

```bash
kubectl --context=kind-agentforge get pods -n agentforge
kubectl --context=kind-agentforge get services -n agentforge
kubectl --context=kind-agentforge get pvc -n agentforge
```

The backend, frontend, and PostgreSQL pods should be running and ready.

The `chroma-data`, `postgres-data`, and `reports-data` claims should be bound.

### Deploy both application images

Configure `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env.local`, or provide it as an environment variable.

Use a Clerk publishable key beginning with `pk_test_` or `pk_live_`.

From the project root, with a clean, committed working tree, run:

```bash
./scripts/deploy-kind.sh
```

The script:

- Checks the required tools and existing cluster.
- Reads the Clerk publishable key without an interactive prompt.
- Builds the backend and frontend images with the current Git commit tag.
- Builds the frontend with `VITE_API_URL=/api`.
- Loads both images into the `agentforge` kind cluster.
- Renders temporary deployment manifests containing the versioned images.
- Applies them using the explicit `kind-agentforge` context.
- Waits for both deployments to become ready.
- Prints the deployed image references.

The script does not edit the tracked deployment manifests. Reapplying those files directly can restore the older image tags recorded in them.

The image tag identifies the Git commit used to build the application. Local frontend configuration is supplied separately at build time.

### Open the dashboard

Run this in a dedicated terminal and leave it running:

```bash
kubectl --context=kind-agentforge port-forward \
  -n agentforge service/agentforge-frontend 8081:80
```

Open http://127.0.0.1:8081 and sign in through Clerk.

The frontend’s nginx proxy forwards `/api/` requests to FastAPI.

If the frontend pod is replaced during deployment, restart the port-forward if it stops.

### Check health and readiness

With the port-forward running:

```bash
curl http://127.0.0.1:8081/api/health
curl http://127.0.0.1:8081/api/ready
```

Expected health response:

```json
{"status":"healthy","service":"AgentForge"}
```

Expected readiness response:

```json
{"status":"ready","service":"AgentForge"}
```

After deploying, also sign in to the dashboard, send a chat request, and check the evaluation results.

### Evaluation report storage

The backend mounts the `reports-data` persistent volume at `/app/reports`.

This allows reports to survive pod replacement while the container’s root filesystem remains read-only.

To import local JSON reports after the deployment is ready:

```bash
AGENTFORGE_POD=$(kubectl --context=kind-agentforge get pods \
  -n agentforge \
  -l app=agentforge \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

kubectl --context=kind-agentforge cp \
  reports/. "agentforge/${AGENTFORGE_POD}:/app/reports"

kubectl --context=kind-agentforge exec \
  -n agentforge "$AGENTFORGE_POD" -- ls -1 /app/reports
```

Refresh the dashboard to view the imported reports.

If no reports have been imported or generated in the mounted directory, the dashboard may display “No evaluation reports found.”

### Verify report persistence

List the reports before replacing the backend pod:

```bash
kubectl --context=kind-agentforge exec \
  -n agentforge deployment/agentforge -- ls -1 /app/reports
```

Restart the deployment and wait for it to become ready:

```bash
kubectl --context=kind-agentforge rollout restart \
  deployment/agentforge -n agentforge

kubectl --context=kind-agentforge rollout status \
  deployment/agentforge -n agentforge --timeout=180s
```

List the reports again:

```bash
kubectl --context=kind-agentforge exec \
  -n agentforge deployment/agentforge -- ls -1 /app/reports
```

The same report filenames should remain available.

Report persistence across a backend rollout was verified on 5 October 2026.

These local volumes are not backups. Deleting the kind cluster or its storage can remove the stored data.

### View Kubernetes logs

```bash
kubectl --context=kind-agentforge logs \
  -n agentforge deployment/agentforge --tail=100
```

To follow logs continuously:

```bash
kubectl --context=kind-agentforge logs \
  -n agentforge deployment/agentforge -f
```

### Check deployed image versions

```bash
kubectl --context=kind-agentforge get deployments \
  -n agentforge \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image'
```

After running the deployment script, the backend and frontend should use the Git commit tag built by that run.

### Kubernetes troubleshooting

**Connection refused on port 8081:** Start or restart the frontend port-forward.

**The deployment script refuses to run:** Check for uncommitted or untracked files:

```bash
git status --short
```

Review and commit or stash appropriate changes before deploying.

**The frontend build fails because the Clerk key is missing:** Check that `VITE_CLERK_PUBLISHABLE_KEY` is set in `frontend/.env.local` or the environment.

**The dashboard returns 404 for `/evaluations`:** Check that the deployed backend includes the route:

```bash
kubectl --context=kind-agentforge exec \
  -n agentforge deployment/agentforge \
  -- python -c 'from app.api import app; print([r.path for r in app.routes if "evaluation" in r.path])'
```

Expected output includes:

```text
['/evaluations']
```

If the route is missing, deploy the current committed code:

```bash
./scripts/deploy-kind.sh
```

**Writing reports fails with “Read-only file system”:** Confirm that the deployment mounts the `reports-data` claim at `/app/reports`. The root filesystem is intentionally read-only.

## Development status

AgentForge is under active development.

Docker Compose and local Kubernetes deployment have been tested. The Kubernetes setup supports authenticated chat, streaming tool execution, and evaluation reports stored on a persistent volume.

The current setup is intended for local development and testing. Production hosting, backups, and production deployment documentation remain future work.
