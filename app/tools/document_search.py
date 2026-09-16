from langchain.tools import tool

from app.rag.vector_store import get_vector_store


@tool
def search_documents(query: str) -> str:
    """Search internal documents for information relevant to a question."""

    vector_store = get_vector_store()

    documents = vector_store.similarity_search(
        query,
        k=3,
    )

    if not documents:
        return "No relevant information was found in the documents."

    results = []

    for document in documents:
        source = document.metadata.get("source", "unknown")

        results.append(
            f"Source: {source}\n"
            f"Content: {document.page_content}"
        )

    return "\n\n---\n\n".join(results)
