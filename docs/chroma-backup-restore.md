# Chroma backup and restore verification

This procedure applies to the local `kind-agentforge` cluster,
`agentforge` namespace, and `chroma-data` persistent volume claim.

## Create a backup

From the repository root:

```bash
./scripts/backup-chroma-kind.sh
```

The script expects exactly one backend replica. It temporarily scales the
backend to zero and waits for its pods to disappear before copying Chroma.
Document search and backend requests are unavailable during this interval.

A helper pod uses the deployed backend image and mounts Chroma read-only.
The script archives the volume, checks the archive listing for
`chroma.sqlite3`, and verifies the archive checksum.

Each timestamped directory under `backups/` contains:

- `chroma.tar.gz`: Chroma database and index files.
- `chroma-contents.txt`: Archive contents.
- `backend-image.txt`: Deployed backend image reference.
- `SHA256SUMS`: Archive checksum.
- `COMPLETE`: Archive creation and checksum verification finished.

The cleanup handler deletes the helper pod and attempts to restore the
original backend replica count, including when the script fails or is
interrupted. Inspect the script exit status and deployment readiness.
`COMPLETE` alone does not confirm successful backend recovery.

```bash
kubectl --context=kind-agentforge -n agentforge get pods
kubectl --context=kind-agentforge -n agentforge \
  rollout status deployment/agentforge --timeout=180s
```

With the frontend port-forward running:

```bash
curl --max-time 10 -fsS http://127.0.0.1:8081/api/health
curl --max-time 10 -fsS http://127.0.0.1:8081/api/ready
```

If automatic backend recovery fails, inspect the pods and restore the
expected replica count:

```bash
kubectl --context=kind-agentforge -n agentforge \
  scale deployment agentforge --replicas=1
kubectl --context=kind-agentforge -n agentforge \
  rollout status deployment/agentforge --timeout=180s
```

## Verify a restore in isolation

Use Python 3.12 with the project's Chroma dependency installed.
The successful verification on 5 October 2026 used Chroma 1.5.9.

Set the completed backup directory:

```bash
export BACKUP_DIR=backups/YOUR_CHROMA_BACKUP_DIRECTORY
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)
```

Proceed only if checksum verification succeeds. Run:

```bash
python - <<'VERIFY'
import os
import sqlite3
import tarfile
import tempfile
from pathlib import Path
import chromadb

backup = Path(os.environ["BACKUP_DIR"])
if not (backup / "COMPLETE").is_file():
    raise SystemExit("Backup completion marker missing.")

restore = Path(tempfile.mkdtemp(prefix="chroma-restore-test-"))
with tarfile.open(backup / "chroma.tar.gz", "r:gz") as archive:
    archive.extractall(restore, filter="data")

database = restore / "chroma.sqlite3"
if not database.is_file():
    raise SystemExit("Restored SQLite database missing.")

with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
    integrity = connection.execute("PRAGMA integrity_check").fetchall()
print("SQLite integrity:", integrity)
if integrity != [("ok",)]:
    raise SystemExit("FAIL: SQLite integrity check failed.")

client = chromadb.PersistentClient(path=str(restore))
collection = client.get_collection(
    "agentforge_docs", embedding_function=None
)
count = collection.count()
print("Restored records:", count)
if count == 0:
    raise SystemExit("FAIL: collection is empty.")

sample = collection.get(limit=1, include=["embeddings", "documents"])
embeddings = sample["embeddings"]
if embeddings is None or len(embeddings) == 0:
    raise SystemExit("FAIL: no stored embedding found.")

vector = embeddings[0].tolist()
print("Embedding dimension:", len(vector))
result = collection.query(
    query_embeddings=[vector],
    n_results=min(3, count),
    include=["documents", "distances"]
)
print("Retrieved IDs:", result["ids"][0])
print("Distances:", result["distances"][0])

if sample["ids"][0] not in result["ids"][0]:
    raise SystemExit(
        "CHECK: source record not returned; investigate ties or index behaviour."
    )

for document in result["documents"][0]:
    print("Document preview:", (document or "")[:200])

print("PASS: restored collection supports vector retrieval.")
print("Test copy:", restore)
VERIFY
```

This operates on a new temporary copy, leaving the live volume unchanged.
It uses a stored embedding and does not call an embedding API.

Checksum verification, SQLite integrity, and vector retrieval from a
restored `agentforge_docs` collection passed on 5 October 2026.
The collection used 1536-dimensional embeddings.

This is an isolated restore test, not a live-volume recovery procedure.
It does not verify every record, retrieval quality for new questions,
or end-to-end application recovery.

## Backup scope and storage

Chroma is backed up separately from PostgreSQL and evaluation reports.
These backups do not form a single synchronized application snapshot.

Backups are excluded from Git and may contain private documents.
Copy completed backups to a separate secure location to protect against
loss of the computer. A backup stored only beside the repository does not
protect against disk failure.
