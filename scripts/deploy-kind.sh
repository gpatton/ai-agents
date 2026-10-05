#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

for tool in git python docker kind kubectl; do
  command -v "$tool" >/dev/null || {
    echo "Missing required tool: $tool" >&2
    exit 1
  }
done

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit or stash your changes before deploying a Git-tagged build." >&2
  exit 1
fi

VERSION=$(git rev-parse --short HEAD)
CONTEXT=kind-agentforge

CLERK_KEY=$(python - <<'PY'
from pathlib import Path
import os

key = os.environ.get("VITE_CLERK_PUBLISHABLE_KEY", "").strip()
if not key:
    path = Path("frontend/.env.local")
    if path.exists():
        for line in path.read_text().splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name.strip() == "VITE_CLERK_PUBLISHABLE_KEY":
                key = value.strip().strip("\"'")
                break

if not key.startswith(("pk_test_", "pk_live_")):
    raise SystemExit("Set a valid VITE_CLERK_PUBLISHABLE_KEY in frontend/.env.local or the environment.")
print(key)
PY
)

kind get clusters | python -c '
import sys
if "agentforge" not in sys.stdin.read().split():
    raise SystemExit("The agentforge kind cluster does not exist.")
'
kubectl --context="$CONTEXT" get namespace agentforge >/dev/null

docker build -t "agentforge:$VERSION" .
docker build \
  --build-arg VITE_API_URL=/api \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="$CLERK_KEY" \
  -t "agentforge-frontend:$VERSION" ./frontend

kind load docker-image \
  "agentforge:$VERSION" \
  "agentforge-frontend:$VERSION" \
  --name agentforge

RENDER_DIR=$(mktemp -d)
trap 'rm -rf "$RENDER_DIR"' EXIT

kubectl set image --local \
  -f k8s/agentforge-deployment.yaml \
  "agentforge=agentforge:$VERSION" \
  -o yaml > "$RENDER_DIR/backend.yaml"

kubectl set image --local \
  -f k8s/frontend-deployment.yaml \
  "frontend=agentforge-frontend:$VERSION" \
  -o yaml > "$RENDER_DIR/frontend.yaml"

kubectl --context="$CONTEXT" apply \
  -f "$RENDER_DIR/backend.yaml" \
  -f "$RENDER_DIR/frontend.yaml"

kubectl --context="$CONTEXT" rollout status \
  deployment/agentforge -n agentforge --timeout=180s
kubectl --context="$CONTEXT" rollout status \
  deployment/agentforge-frontend -n agentforge --timeout=180s

kubectl --context="$CONTEXT" get deployments -n agentforge \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image'

echo "Deployed version $VERSION. Refresh the dashboard and test chat and evaluations."
