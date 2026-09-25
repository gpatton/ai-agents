#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="agentforge"
ENV_FILE=".env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: $ENV_FILE not found."
    exit 1
fi

# Load local environment variables.
set -a
source "$ENV_FILE"
set +a

# Verify required secrets exist.
: "${OPENAI_API_KEY:?OPENAI_API_KEY is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

# Create/update the application's secrets without writing
# secret values to a Kubernetes YAML file.
kubectl create secret generic agentforge-secrets \
    --namespace "$NAMESPACE" \
    --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
    --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    --dry-run=client \
    -o yaml \
    | kubectl apply -f -

# Construct the Kubernetes-specific database URL.
DATABASE_URL="postgresql://agentforge:${POSTGRES_PASSWORD}@postgres:5432/agentforge"

kubectl create secret generic agentforge-db-url \
    --namespace "$NAMESPACE" \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --dry-run=client \
    -o yaml \
    | kubectl apply -f -

echo "AgentForge Kubernetes secrets created/updated successfully."
