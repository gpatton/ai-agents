import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


DATA_FILE = Path("data/company_handbook.txt")
COLLECTION_NAME = "agentforge_docs"
FINGERPRINT_FILE = Path(settings.chroma_dir) / "document.sha256"


def load_document() -> str:
    """Load the AgentForge handbook."""
    return DATA_FILE.read_text(encoding="utf-8")


def get_embeddings() -> OpenAIEmbeddings:
    """Create the embedding model used by the vector store."""
    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )


def get_vector_store() -> Chroma:
    """Return the persistent AgentForge Chroma vector store."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )


def create_document_id(
    content: str,
    index: int,
) -> str:
    """Create a deterministic ID for a document chunk."""
    value = f"{DATA_FILE}:{index}:{content}"

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def get_document_fingerprint() -> str:
    """Return a SHA-256 fingerprint of the source document."""
    content = DATA_FILE.read_bytes()

    return hashlib.sha256(content).hexdigest()


def get_indexed_fingerprint() -> str | None:
    """Return the fingerprint used for the current index."""
    if not FINGERPRINT_FILE.exists():
        return None

    return FINGERPRINT_FILE.read_text(
        encoding="utf-8"
    ).strip()


def save_indexed_fingerprint(
    fingerprint: str,
) -> None:
    """Save the fingerprint associated with the current index."""
    FINGERPRINT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    FINGERPRINT_FILE.write_text(
        fingerprint,
        encoding="utf-8",
    )


def vector_store_has_documents() -> bool:
    """Return True when the vector store contains documents."""
    vector_store = get_vector_store()

    return vector_store._collection.count() > 0


def vector_store_needs_indexing() -> bool:
    """Return True when the document index needs rebuilding."""
    current_fingerprint = get_document_fingerprint()
    indexed_fingerprint = get_indexed_fingerprint()

    if indexed_fingerprint != current_fingerprint:
        return True

    return not vector_store_has_documents()


def clear_vector_store() -> None:
    """Delete the AgentForge Chroma collection."""
    vector_store = get_vector_store()

    try:
        vector_store.delete_collection()
    except ValueError:
        # The collection may not exist yet.
        pass


def create_vector_store() -> Chroma:
    """Rebuild the AgentForge document index."""
    text = load_document()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    documents = splitter.create_documents(
        [text],
        metadatas=[
            {
                "source": str(DATA_FILE),
            }
        ],
    )

    ids = [
        create_document_id(
            document.page_content,
            index,
        )
        for index, document in enumerate(documents)
    ]

    # Remove the previous collection so stale chunks
    # cannot survive a document update.
    clear_vector_store()

    # Opening the vector store again creates a fresh
    # collection after the previous one was deleted.
    vector_store = get_vector_store()

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    # Only save the fingerprint after indexing succeeds.
    save_indexed_fingerprint(
        get_document_fingerprint()
    )

    return vector_store 

