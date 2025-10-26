
from typing import Any, TypedDict
from langchain_qdrant.fastembed_sparse import FastEmbedSparse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    NamedSparseVector,
    ScoredPoint,
    SparseVector,
)



class ChunkResult(TypedDict):
    id: str
    score: float
    payload: dict[str, Any]



def query(
        sparse_embeddings: FastEmbedSparse,
    qdrant_client: QdrantClient,
    collection: str,
    search_input: str,
    limit: int,
    threshold: float | None = None,
    sparse_multiplier: float = 8.0,
) -> list[ChunkResult]:
    """Perform hybrid (dense + sparse) search in Qdrant.

    Args:
        qdrant_client: QdrantClient instance.
        collection: Qdrant collection name.
        search_input: Query string.
        limit: Max results per vector type.
        threshold: Optional score threshold.
        sparse_multiplier: Multiplier for sparse score threshold.

    Returns:
        List of ChunkResult sorted by descending score.
    """
    sparse_vector_raw = sparse_embeddings.embed_query(search_input)
    sparse_vector = SparseVector(
            indices=sparse_vector_raw.indices, values=sparse_vector_raw.values
        )

    try:
        
        search_results:list[ScoredPoint]=qdrant_client.search(collection_name=collection, query_vector=NamedSparseVector(name="text-sparse", vector=sparse_vector),limit=limit,with_payload=True,score_threshold=threshold * sparse_multiplier if threshold else None)
    except Exception as e:
        raise ValueError(f"Query to database failed due to error: {e}") from e


    # Convert to ChunkResult and sort by score descending
    chunk_results: list[ChunkResult] = [
        {"id": str(p.id), "score": p.score, "payload": p.payload or {}}
        for p in search_results
        if p.payload is not None
    ]

    chunk_results.sort(key=lambda x: x["score"], reverse=True)

    return chunk_results