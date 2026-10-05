#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(git rev-parse --show-toplevel)"

CONTEXT=kind-agentforge
mkdir -p backups
BACKUP_DIR=$(mktemp -d "backups/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")

echo "Creating backup in $BACKUP_DIR"

# Create a PostgreSQL custom-format archive.
kubectl --context="$CONTEXT" exec \
  -n agentforge deployment/postgres \
  -- pg_dump -U agentforge -d agentforge -Fc \
  > "$BACKUP_DIR/postgres.dump.partial"

test -s "$BACKUP_DIR/postgres.dump.partial"
mv "$BACKUP_DIR/postgres.dump.partial" "$BACKUP_DIR/postgres.dump"

# Check that PostgreSQL can read the archive's table of contents.
kubectl --context="$CONTEXT" exec -i \
  -n agentforge deployment/postgres \
  -- pg_restore --list \
  < "$BACKUP_DIR/postgres.dump" \
  > "$BACKUP_DIR/postgres-contents.txt"

# Archive the reports from the mounted persistent volume.
kubectl --context="$CONTEXT" exec \
  -n agentforge deployment/agentforge \
  -- tar -C /app/reports -czf - . \
  > "$BACKUP_DIR/reports.tar.gz.partial"

tar -tzf "$BACKUP_DIR/reports.tar.gz.partial" \
  > "$BACKUP_DIR/reports-contents.txt"

mv "$BACKUP_DIR/reports.tar.gz.partial" "$BACKUP_DIR/reports.tar.gz"

# Record application image versions.
kubectl --context="$CONTEXT" get deployments \
  -n agentforge \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image' \
  > "$BACKUP_DIR/images.txt"

(
  cd "$BACKUP_DIR"
  sha256sum postgres.dump reports.tar.gz > SHA256SUMS
  sha256sum -c SHA256SUMS
)

touch "$BACKUP_DIR/COMPLETE"
echo "Backup completed: $BACKUP_DIR"
echo "Archive checks passed. A database restore test is still required."
