"""
Lambda-friendly vector RAG with Chroma.

The original local version used sentence-transformers, which pulls PyTorch and makes
Lambda container images heavy. This version uses a deterministic character n-gram
hash embedding so the AWS demo can run without model downloads or GPU libraries.

For best results, build the AWS index with:
    python scripts/build_aws_vector_index.py
"""
import hashlib
import logging
import math
import os
import re
import shutil
import warnings
from pathlib import Path
from typing import Dict, List, Optional

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*telemetry.*")

import chromadb
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PatentTranslation

logger = logging.getLogger(__name__)


class HashEmbedding:
    """Small deterministic embedding for Japanese patent demo retrieval."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, text: str) -> list[float]:
        normalized = self._normalize(text)
        features = self._features(normalized)
        vector = [0.0] * self.dim

        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dim
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", text or "").lower()

    def _features(self, text: str) -> list[str]:
        if not text:
            return []

        features: list[str] = []
        for n in (2, 3, 4):
            if len(text) >= n:
                features.extend(text[i:i + n] for i in range(len(text) - n + 1))
        features.extend(re.findall(r"[A-Za-z0-9_\-]+", text))
        return features or [text]


class VectorRAG:
    """Vector-based Retrieval Augmented Generation using bundled Chroma."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        configured_directory = persist_directory or settings.CHROMA_DB_DIR
        self.persist_directory = self._prepare_lambda_chroma_dir(configured_directory)
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.embedding_model = HashEmbedding(dim=settings.VECTOR_EMBEDDING_DIM)

        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "VectorRAG initialized: %s embeddings in %s/%s",
            self.collection.count(),
            self.persist_directory,
            self.collection_name,
        )

    def _prepare_lambda_chroma_dir(self, configured_directory: str) -> str:
        """Copy bundled Chroma files to /tmp in Lambda because the image filesystem is read-only."""
        if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return configured_directory

        source = Path(configured_directory)
        target = Path("/tmp/aws_chroma_db")

        if target.exists():
            return str(target)

        if source.exists() and any(source.iterdir()):
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            target.mkdir(parents=True, exist_ok=True)

        return str(target)

    def add_translation(
        self,
        translation_id: int,
        source_text: str,
        translation_text: str,
        metadata: Dict,
    ):
        embedding = self.embedding_model.encode(source_text)
        safe_metadata = {
            "translation_id": str(translation_id),
            "translation": (translation_text or "")[:1000],
            "section_type": metadata.get("section_type", "") or "",
            "domain": metadata.get("domain", "") or "",
            "patent_id": metadata.get("patent_id", "") or "",
        }

        self.collection.upsert(
            embeddings=[embedding],
            documents=[(source_text or "")[:1500]],
            metadatas=[safe_metadata],
            ids=[f"trans_{translation_id}"],
        )

    def search_similar(
        self,
        query_text: str,
        domain: Optional[str] = None,
        section_type: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict]:
        try:
            if self.collection.count() == 0:
                return []

            query_embedding = self.embedding_model.encode(query_text)

            where_filter = {}
            if domain:
                where_filter["domain"] = domain
            if section_type and section_type != "general":
                where_filter["section_type"] = section_type

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None,
            )

            similar_translations = []
            ids = results.get("ids") or [[]]
            documents = results.get("documents") or [[]]
            metadatas = results.get("metadatas") or [[]]
            distances = results.get("distances") or [[]]

            for index in range(len(ids[0])):
                metadata = metadatas[0][index] or {}
                distance = distances[0][index] if distances and distances[0] else None
                similarity = 1 - distance if isinstance(distance, (int, float)) else None

                try:
                    translation_id = int(metadata.get("translation_id", 0))
                except Exception:
                    translation_id = 0

                source_text = documents[0][index] or ""
                translation_text = metadata.get("translation", "") or ""

                query_len = len(query_text.strip())
                source_len = len(source_text.strip())

                if query_len < 120 and source_len > 500:
                    continue

                similar_translations.append({
                    "id": translation_id,
                    "source_text": source_text[:300].rstrip(),
                    "translation": translation_text[:300].rstrip(),
                    "similarity_score": similarity,
                    "domain": metadata.get("domain", ""),
                    "section_type": metadata.get("section_type", ""),
                })

            return similar_translations
        except Exception as exc:
            logger.error("Error searching vector index: %s", exc)
            return []

    def build_index_from_db(self, db: Session, batch_size: int = 100):
        total = db.query(PatentTranslation).count()
        logger.info("Building vector index from %s database translations", total)

        indexed = 0
        for offset in range(0, total, batch_size):
            batch = db.query(PatentTranslation).offset(offset).limit(batch_size).all()
            for translation in batch:
                self.add_translation(
                    translation_id=translation.id,
                    source_text=translation.source_text,
                    translation_text=translation.translation,
                    metadata={
                        "section_type": translation.section_type or "",
                        "domain": translation.domain or "",
                        "patent_id": translation.patent_id or "",
                    },
                )
                indexed += 1

        logger.info("AWS vector index complete: %s translations indexed", indexed)
        return indexed
