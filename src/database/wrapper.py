
from collections.abc import Sequence
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import ExtendedPointId, PointIdsList
from langchain_qdrant import FastEmbedSparse

from src.environment import (
    NGINX_PASSWORD,
    QDRANT_COLLECTION_NAME,
    QDRANT_RESULT_LIMIT,
    QDRANT_URL,
    SPARSE_EMBEDDING_MODEL
)
from src.database.structure import ChunkResult, CollectionPoint, PointPayload
from src.database.query import query
from src.database.utils import check_create_collection, delete_collection, embed_and_save_chunks, get_points
from utils import num_tokens_from_string


@dataclass
class QDrantWrapperClientParams:
    url: str
    collection_name: str


class QDrantWrapperClient:
    def __init__(self, props: QDrantWrapperClientParams) -> None:
        self.props = props
        self.client = QdrantClient(
            location=props.url,
            api_key=NGINX_PASSWORD,
            https=True,
        )
        self.sparse_embeddings=FastEmbedSparse(
            model_name=SPARSE_EMBEDDING_MODEL,
            batch_size=128,
            cache_dir=".cache/fastembed"
        )

        check_create_collection(
            self.client, props.collection_name
        )

    def delete_collection(self, collection_name: str):
        return delete_collection(self.client, collection_name)

    def get_all_points(self) -> list[CollectionPoint]:
        return get_points(
            self.client,
            self.props.collection_name,
        )

    def measure_average_tokens(self):
        collection=self.get_all_points()
        collection_len = len(collection)
        total_token_count = 0
        for point in collection:
            total_token_count += num_tokens_from_string(point.payload.chunk_text)
        return total_token_count / collection_len

    def embed_and_save_chunks(self, chunks: list[PointPayload]):
        return embed_and_save_chunks(
            self.client,
            self.sparse_embeddings,
            self.props.collection_name,
            chunks,
        )

    def query(
        self,
        search_input: str,
        max_results: int = QDRANT_RESULT_LIMIT,
        threshold: float | None = None,
    ) -> list[ChunkResult]:
        return query(
            self.sparse_embeddings,
            self.client,
            self.props.collection_name,
            search_input,
            limit=max_results,
            threshold=threshold,
        )

    def delete(self, points_selector: Sequence[ExtendedPointId]):
        return self.client.delete(
            self.props.collection_name,
            points_selector=PointIdsList(points=list(points_selector)),
        )

    def get_point_by_id(self, point_id: str):
        result = self.client.retrieve(
            collection_name=self.props.collection_name, ids=[point_id]
        )
        return result[0] if result else None


print(
    "Qdrant Settings:",
    QDRANT_URL,
    QDRANT_COLLECTION_NAME,
    NGINX_PASSWORD,
)

default_qdrant_client = QDrantWrapperClient(
    QDrantWrapperClientParams(
        QDRANT_URL,
        QDRANT_COLLECTION_NAME,
    )
)
