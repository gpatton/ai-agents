from unittest.mock import Mock

from langchain_core.documents import Document

from app.tools import document_search


def test_relevant_document_is_returned(monkeypatch):
    fake_store = Mock()

    fake_store.similarity_search_with_relevance_scores.return_value = [
        (
            Document(
                page_content="Employees receive 25 days annual leave.",
                metadata={"source": "handbook.txt"},
            ),
            0.40,
        )
    ]

    monkeypatch.setattr(
        document_search,
        "get_vector_store",
        lambda: fake_store,
    )

    result = document_search.search_document_content(
        "How much annual leave do employees receive?"
    )

    assert "25 days" in result
    assert "handbook.txt" in result


def test_irrelevant_document_is_rejected(monkeypatch):
    fake_store = Mock()

    fake_store.similarity_search_with_relevance_scores.return_value = [
        (
            Document(
                page_content="Employees receive 25 days annual leave.",
                metadata={"source": "handbook.txt"},
            ),
            -0.20,
        )
    ]

    monkeypatch.setattr(
        document_search,
        "get_vector_store",
        lambda: fake_store,
    )

    result = document_search.search_document_content(
        "What is the capital of France?"
    )

    assert result == (
        "No relevant information was found "
        "in the internal documents."
    )


def test_result_below_threshold_is_rejected(monkeypatch):
    fake_store = Mock()

    fake_store.similarity_search_with_relevance_scores.return_value = [
        (
            Document(
                page_content="Some weakly related content.",
                metadata={"source": "handbook.txt"},
            ),
            0.24,
        )
    ]

    monkeypatch.setattr(
        document_search,
        "get_vector_store",
        lambda: fake_store,
    )

    result = document_search.search_document_content(
        "Unrelated question"
    )

    assert "No relevant information" in result
