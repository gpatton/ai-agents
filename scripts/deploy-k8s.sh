#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="agentforge"
CLUSTER="agentforge"

echo "=== Deploying AgentForge to Kubernetes ==="

# ---------------------------------------------------------
# Preflight
# ---------------------------------------------------------

echo "Checking kind cluster..."

if ! kind get clusters | grep -qx "$CLUSTER"; then
    echo "Error: kind cluster '$CLUSTER' does not exist."
    exit 1
fi

# ---------------------------------------------------------
# Container images
# ---------------------------------------------------------

echo "Checking Docker images..."

for IMAGE in agentforge:latest agentforge-frontend:k8s; do
    if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
        echo "Error: Docker image $IMAGE does not exist."
        exit 1
    fi
done

echo "Loading backend image..."
kind load docker-image agentforge:latest --name "$CLUSTER"

echo "Loading frontend image..."
kind load docker-image agentforge-frontend:k8s --name "$CLUSTER"

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
# Backend
# ---------------------------------------------------------

echo "Deploying AgentForge backend..."

kubectl apply -f k8s/agentforge-service.yaml
kubectl apply -f k8s/agentforge-deployment.yaml

echo "Waiting for backend..."

kubectl rollout status \
    deployment/agentforge \
    -n "$NAMESPACE" \
    --timeout=180s

# ---------------------------------------------------------
# Frontend
# ---------------------------------------------------------

echo "Deploying AgentForge frontend..."

kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml

echo "Waiting for frontend..."

kubectl rollout status \
    deployment/agentforge-frontend \
    -n "$NAMESPACE" \
    --timeout=120s

# ---------------------------------------------------------
# Status
# ---------------------------------------------------------

echo
echo "=== AgentForge deployment complete ==="
echo

kubectl get pods,services,pvc -n "$NAMESPACE"

echo
echo "Frontend:"
echo "kubectl port-forward -n agentforge service/agentforge-frontend 8081:80"

echo
echo "Backend:"
echo "kubectl port-forward -n agentforge service/agentforge 8002:8000"
