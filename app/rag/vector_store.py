from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


DATA_FILE = Path("data/company_handbook.txt")
CHROMA_DIR = "chroma_db"


def load_document() -> str:
    """Load the company handbook."""

    return DATA_FILE.read_text(encoding="utf-8")


def create_vector_store():
    """Split the document, create embeddings and store them in Chroma."""

    text = load_document()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    documents = splitter.create_documents(
        [text],
        metadatas=[{"source": str(DATA_FILE)}],
    )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vector_store = Chroma(
        collection_name="agentforge_docs",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )

    vector_store.add_documents(documents)

    return vector_store


def get_vector_store():
    """Open the existing Chroma vector store."""

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    return Chroma(
        collection_name="agentforge_docs",
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
