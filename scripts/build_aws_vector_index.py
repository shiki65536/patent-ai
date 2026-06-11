"""Build a lightweight Chroma index for AWS Lambda deployment.

This uses the same HashEmbedding implementation as app.services.vector_rag, so the
runtime does not need sentence-transformers or PyTorch.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.database import SessionLocal
from app.services.vector_rag import VectorRAG


def main() -> None:
    chroma_dir = Path(settings.CHROMA_DB_DIR)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    db = SessionLocal()
    try:
        rag = VectorRAG(
            persist_directory=settings.CHROMA_DB_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
        )
        count = rag.build_index_from_db(db)
        print(f"Built AWS vector index: {count} translations")
        print(f"Directory: {settings.CHROMA_DB_DIR}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
