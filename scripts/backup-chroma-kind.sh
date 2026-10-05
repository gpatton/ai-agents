#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(git rev-parse --show-toplevel)"

CONTEXT=kind-agentforge
NAMESPACE=agentforge
HELPER="chroma-backup-$(date -u +%Y%m%d%H%M%S)-$$"
RESTORE_REQUIRED=0

k() {
  kubectl --context="$CONTEXT" -n "$NAMESPACE" "$@"
}

REPLICAS=$(k get deployment agentforge -o jsonpath='{.spec.replicas}')
IMAGE=$(k get deployment agentforge \
  -o jsonpath='{.spec.template.spec.containers[0].image}')

if [[ "$REPLICAS" != "1" ]]; then
  echo "Expected one backend replica; found $REPLICAS. Nothing changed." >&2
  exit 1
fi

mkdir -p backups
BACKUP_DIR=$(mktemp -d "backups/chroma-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")

cleanup() {
  local result=$?
  trap - EXIT
  k delete pod "$HELPER" --ignore-not-found --wait=true \
    --timeout=60s || result=1

  if [[ "$RESTORE_REQUIRED" == "1" ]]; then
    k scale deployment agentforge --replicas="$REPLICAS" || result=1
    k rollout status deployment/agentforge --timeout=180s || result=1
  fi

  if [[ "$result" != "0" ]]; then
    echo "Backup or recovery failed. Check backend status." >&2
    echo "Recovery command: kubectl --context=$CONTEXT -n $NAMESPACE scale deployment agentforge --replicas=$REPLICAS" >&2
  fi
  exit "$result"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '%s\n' "$IMAGE" > "$BACKUP_DIR/backend-image.txt"

echo "Stopping the backend for a Chroma backup..."
RESTORE_REQUIRED=1
k scale deployment agentforge --replicas=0
k wait --for=delete pod -l app=agentforge --timeout=180s

k create -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $HELPER
spec:
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
  containers:
    - name: backup
      image: $IMAGE
      imagePullPolicy: Never
      command: ["python", "-c", "import time; time.sleep(3600)"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: chroma
          mountPath: /backup/chroma
          readOnly: true
  volumes:
    - name: chroma
      persistentVolumeClaim:
        claimName: chroma-data
        readOnly: true
EOF

k wait --for=condition=Ready "pod/$HELPER" --timeout=120s

k exec "$HELPER" -- tar -C /backup/chroma -czf - . \
  > "$BACKUP_DIR/chroma.tar.gz.partial"

tar -tzf "$BACKUP_DIR/chroma.tar.gz.partial" \
  > "$BACKUP_DIR/chroma-contents.txt"

# Confirm the archive includes Chroma's SQLite database.
if ! grep -Fxq './chroma.sqlite3' "$BACKUP_DIR/chroma-contents.txt"; then
  echo "Chroma database missing from archive." >&2
  exit 1
fi

mv "$BACKUP_DIR/chroma.tar.gz.partial" "$BACKUP_DIR/chroma.tar.gz"

(
  cd "$BACKUP_DIR"
  sha256sum chroma.tar.gz > SHA256SUMS
  sha256sum -c SHA256SUMS
)

touch "$BACKUP_DIR/COMPLETE"
echo "Archive created: $BACKUP_DIR"
echo "Restarting the backend during cleanup..."
