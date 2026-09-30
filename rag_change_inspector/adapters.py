"""Duck-typed Chroma adapter; collection configuration controls embedding execution."""

from .core import validate


def snapshot_chroma(collection, questions, *, k=5, query_embeddings=None):
    """questions: [{id, text, relevant_sources}]. Provide embeddings to avoid text embedding calls."""
    if type(k) is not int or k < 1:
        raise ValueError("k must be positive")
    if not isinstance(questions, list) or not questions:
        raise ValueError("Provide at least one question")
    validate({"questions": [{**q, "results": []} for q in questions]})
    if query_embeddings is not None and len(query_embeddings) != len(questions):
        raise ValueError("One embedding is required per question")
    payload = (
        {"query_embeddings": query_embeddings}
        if query_embeddings is not None
        else {"query_texts": [q["text"] for q in questions]}
    )
    result = collection.query(
        **payload, n_results=k, include=["documents", "metadatas"]
    )
    rows = []
    for index, question in enumerate(questions):
        ranking = []
        for position, chunk_id in enumerate(result["ids"][index]):
            metadata = result["metadatas"][index][position] or {}
            if (
                not isinstance(metadata.get("source_id"), str)
                or not metadata["source_id"]
            ):
                raise ValueError("Every Chroma chunk needs a stable metadata.source_id")
            ranking.append(
                {
                    "source_id": metadata["source_id"],
                    "chunk_id": chunk_id,
                    "text": result["documents"][index][position] or "",
                }
            )
        rows.append({**question, "results": ranking})
    snapshot = {"version": 1, "questions": rows}
    validate(snapshot)
    return snapshot
