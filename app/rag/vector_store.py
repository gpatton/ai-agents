import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


DATA_FILE = Path("data/company_handbook.txt")
COLLECTION_NAME = "agentforge_docs"


def load_document() -> str:
    """Load the AgentForge handbook."""

    return DATA_FILE.read_text(encoding="utf-8")


def get_embeddings() -> OpenAIEmbeddings:
    """Create the embedding model."""

    return OpenAIEmbeddings(
        model="text-embedding-3-small"
    )


def get_vector_store() -> Chroma:
    """Return the persistent Chroma vector store."""

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


def create_vector_store() -> Chroma:
    """Index the handbook without creating duplicate chunks."""

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

    vector_store = get_vector_store()

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    return vector_store
