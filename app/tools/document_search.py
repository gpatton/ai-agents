import logging

from langchain.tools import tool

from app.rag.vector_store import get_vector_store


logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.25


def search_document_content(query: str) -> str:
    """Search internal documents for relevant information."""

    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_relevance_scores(
        query,
        k=3,
    )

    relevant_results = [
        (document, score)
        for document, score in results
        if score >= RELEVANCE_THRESHOLD
    ]

    logger.info(
        "RAG search | query=%r | scores=%s",
        query,
        [
            round(score, 4)
            for _, score in results
        ],
    )

    if not relevant_results:
        return (
            "No relevant information was found "
            "in the internal documents."
        )

    formatted_results = []

    for document, score in relevant_results:
        source = document.metadata.get(
            "source",
            "unknown",
        )

        formatted_results.append(
            f"Source: {source}\n"
            f"Relevance: {score:.4f}\n"
            f"Content: {document.page_content}"
        )

    return "\n\n---\n\n".join(formatted_results)


@tool
def search_documents(query: str) -> str:
    """Search internal documents for company information."""

    return search_document_content(query)
