import os

from dotenv import load_dotenv

load_dotenv()


QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_RESULT_LIMIT = int(os.getenv("QDRANT_RESULT_LIMIT", str(10)))
QDRANT_COLLECTION_NAME=os.getenv("QDRANT_COLLECTION_NAME", "")


CONTEXT_LENGTH = os.getenv("CONTEXT_LENGTH", "8192")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen")
SPARSE_EMBEDDING_MODEL = os.getenv("SPARSE_EMBEDDING_MODEL", "Qdrant/bm25")

API_KEY=os.getenv("API_KEY")
OPENAI_COMPAT_URL=os.getenv("OPENAI_COMPAT_URL", "https://api.openai.com/v1")
