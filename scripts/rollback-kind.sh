#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?Usage: ./scripts/rollback-kind.sh GIT_TAG}"
CONTEXT=kind-agentforge

if [[ ! "$VERSION" =~ ^[0-9a-f]{7,40}$ ]]; then
  echo "Provide a Git commit tag containing 7–40 hexadecimal characters." >&2
  exit 1
fi

# Verify both images exist locally before changing the deployment.
docker image inspect "agentforge:$VERSION" >/dev/null
docker image inspect "agentforge-frontend:$VERSION" >/dev/null

kind load docker-image \
  "agentforge:$VERSION" \
  "agentforge-frontend:$VERSION" \
  --name agentforge

kubectl --context="$CONTEXT" set image \
  -n agentforge deployment/agentforge \
  "agentforge=agentforge:$VERSION"

kubectl --context="$CONTEXT" set image \
  -n agentforge deployment/agentforge-frontend \
  "frontend=agentforge-frontend:$VERSION"

kubectl --context="$CONTEXT" rollout status \
  -n agentforge deployment/agentforge --timeout=180s

kubectl --context="$CONTEXT" rollout status \
  -n agentforge deployment/agentforge-frontend --timeout=180s

echo "Both deployments are ready at version $VERSION."
