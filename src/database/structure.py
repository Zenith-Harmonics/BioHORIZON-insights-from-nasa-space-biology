
from dataclasses import dataclass
from typing import Any, TypedDict


@dataclass
class PointPayload:
    registration_timestamp: int
    chunk_text: str
    meta_info: dict | None


@dataclass
class CollectionPoint:
    point_id: str
    payload: PointPayload


class ChunkResult(TypedDict):
    id: str
    score: float
    payload: dict[str, Any]

