import tiktoken
from src.database.structure import ChunkResult


def num_tokens_from_string(string: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))





def convert_results_to_docs(results: list[ChunkResult]) -> list[dict[str, str]]:
    """Convert ChunkResult list to a list of dicts
    with 'id' and 'text' keys, preserving score order."""
    sorted_results = sorted(results, key=lambda r: r["score"], reverse=True)
    return [
        {
            "id": r["id"],
            "text": r["payload"].get("chunk_text") or r["payload"].get("text") or "",
        }
        for r in sorted_results
    ]


def convert_results_to_text(results: list[ChunkResult]) -> list[str]:
    """Convert ChunkResult list to a list of text strings, preserving score order."""
    sorted_results = sorted(results, key=lambda r: r["score"], reverse=True)
    return [
        r["payload"].get("text") or ""
        for r in sorted_results
    ]


def chunkresults_to_strings(chunks: list[ChunkResult]) -> list[str]:
    strings = []
    for chunk in chunks:
        if isinstance(chunk.get("payload"), dict):
            combined = ", ".join(
                str(v) for v in chunk["payload"].values() if v is not None
            )
        else:
            combined = ""
        strings.append(combined)
    return strings


