from app.rag.vector_store import create_document_id
from unittest.mock import Mock
from app.rag import vector_store

def test_document_id_is_deterministic():
    first = create_document_id(
        "Example document",
        0,
    )

    second = create_document_id(
        "Example document",
        0,
    )

    assert first == second


def test_different_content_has_different_id():
    first = create_document_id(
        "Document one",
        0,
    )

    second = create_document_id(
        "Document two",
        0,
    )

    assert first != second


def test_different_chunk_index_has_different_id():
    first = create_document_id(
        "Same document",
        0,
    )

    second = create_document_id(
        "Same document",
        1,
    )

    assert first != second

def test_clear_vector_store_deletes_collection(
    monkeypatch,
):
    fake_store = Mock()

    monkeypatch.setattr(
        vector_store,
        "get_vector_store",
        lambda: fake_store,
    )

    vector_store.clear_vector_store()

    fake_store.delete_collection.assert_called_once()
