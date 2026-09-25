#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="agentforge"

echo "=== Deploying AgentForge to Kubernetes ==="

# ---------------------------------------------------------
# Preflight
# ---------------------------------------------------------

echo "Checking kind cluster..."

if ! kind get clusters | grep -qx "agentforge"; then
    echo "Error: kind cluster 'agentforge' does not exist."
    echo "Create it first with:"
    echo "kind create cluster --name agentforge"
    exit 1
fi

# ---------------------------------------------------------
# Container image
# ---------------------------------------------------------

echo "Checking AgentForge Docker image..."

if ! docker image inspect agentforge:latest >/dev/null 2>&1; then
    echo "Error: agentforge:latest does not exist."
    echo "Build it first with:"
    echo "docker compose build agentforge"
    exit 1
fi

echo "Loading AgentForge image into kind..."

kind load docker-image agentforge:latest --name agentforge

# ---------------------------------------------------------
# Namespace
# ---------------------------------------------------------

echo "Creating namespace..."

kubectl create namespace "$NAMESPACE" \
    --dry-run=client \
    -o yaml \
    | kubectl apply -f -

# ---------------------------------------------------------
# Secrets
# ---------------------------------------------------------

echo "Creating Kubernetes secrets..."

./scripts/create-k8s-secrets.sh

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

echo "Applying AgentForge configuration..."

set -a
source .env
set +a

: "${CLERK_ISSUER:?CLERK_ISSUER is required}"

kubectl create configmap agentforge-config \
    --namespace "$NAMESPACE" \
    --from-literal=CLERK_ISSUER="$CLERK_ISSUER" \
    --dry-run=client \
    -o yaml \
    | kubectl apply -f -

# ---------------------------------------------------------
# Persistent storage
# ---------------------------------------------------------

echo "Applying persistent storage..."

kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/chroma-pvc.yaml

# ---------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------

echo "Deploying PostgreSQL..."

kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-deployment.yaml

echo "Waiting for PostgreSQL..."

kubectl rollout status \
    deployment/postgres \
    -n "$NAMESPACE" \
    --timeout=120s

# ---------------------------------------------------------
# AgentForge
# ---------------------------------------------------------

echo "Deploying AgentForge..."

kubectl apply -f k8s/agentforge-service.yaml
kubectl apply -f k8s/agentforge-deployment.yaml

echo "Waiting for AgentForge..."

kubectl rollout status \
    deployment/agentforge \
    -n "$NAMESPACE" \
    --timeout=180s

# ---------------------------------------------------------
# Status
# ---------------------------------------------------------

echo
echo "=== AgentForge deployment complete ==="
echo

kubectl get pods,services,pvc -n "$NAMESPACE"

echo
echo "To access AgentForge locally:"
echo
echo "kubectl port-forward -n agentforge service/agentforge 8000:8000"
