from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    SparseIndexParams,
    SparseVectorParams,
)
from database.structure import CollectionPoint, PointPayload
import json
import uuid

from qdrant_client.http.models import PointStruct, SparseVector


from langchain_qdrant import FastEmbedSparse



BATCH_SIZE = 1024  # Number of batches per insert in database

def check_create_collection(
    client: QdrantClient, collection_name: str
):
    if not client.collection_exists(collection_name):
        print(f"Creating collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
           
            sparse_vectors_config={
                "text-sparse": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False,
                    )
                )
            },
        )
    else:
        print(f"{collection_name} already exists")


def delete_collection(client: QdrantClient, collection_name: str):
    print("Deleting qdrant collection", collection_name)
    result = client.delete_collection(collection_name)
    if result:
        print("Deletion was successfull")
    else:
        print("Deletion failed")





def get_points(
    client: QdrantClient, collection: str
) -> list[CollectionPoint]:
    chunks: list[CollectionPoint] = []
    offset = None

    while True:
        points_batch, offset = client.scroll(
            collection_name=collection,
            limit=1000,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        for point in points_batch:
            if point.payload is None:
                msg = f"Payload of point {point.id} is None"
                raise ValueError(msg)

            chunk = CollectionPoint(
                point_id=str(point.id),
                payload=PointPayload(
                    registration_timestamp=point.payload["registration_timestamp"],
                    chunk_text=point.payload["text"],
                    meta_info=point.payload["meta_info"],
                ),
            )
            chunks.append(chunk)
        if offset is None:
            break
    return chunks





def embed_and_save_chunks(
    client: QdrantClient,
    sparse_embeddings: FastEmbedSparse,
    collection: str,
    chunks: list[PointPayload],
):
    chunk_json_dumps: list[str] = [json.dumps(chunk.__dict__) for chunk in chunks]

    sparse_vectors = sparse_embeddings.embed_documents(chunk_json_dumps)

    points: list[PointStruct] = []

    for chunk, sparse_vector in zip(
        chunk_json_dumps, sparse_vectors, strict=False
    ):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    "text-sparse": SparseVector(
                        indices=sparse_vector.indices, values=sparse_vector.values
                    ),
                },
                payload=json.loads(chunk),
            )
        )

    print("Embed finished")

    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        client.upsert(collection_name=collection, points=batch)

    print("Save Chunks finished")

