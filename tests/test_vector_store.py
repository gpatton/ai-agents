from app.rag.vector_store import create_document_id


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
