from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import PatentTranslation
from app.services.vector_rag import VectorRAG


class TranslationRAG:
    """Retrieval-Augmented Generation for patent translation."""

    def __init__(self):
        self.vector_rag = None
        if settings.ENABLE_VECTOR_RAG:
            try:
                self.vector_rag = VectorRAG()
            except Exception:
                self.vector_rag = None

    def retrieve_similar_translations(
        self,
        japanese_text: str,
        db: Session,
        domain: Optional[str] = None,
        section_type: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict]:
        """Retrieve similar past translations, preferring Chroma vector search."""

        if self.vector_rag:
            vector_results = self.vector_rag.search_similar(
                japanese_text,
                domain=domain,
                section_type=section_type,
                limit=limit,
            )

            if vector_results:
                return vector_results

        return []

        # query = db.query(PatentTranslation)

        # if domain:
        #     query = query.filter(PatentTranslation.domain == domain)
        # if section_type and section_type != "general":
        #     query = query.filter(PatentTranslation.section_type == section_type)

        # results = query.order_by(PatentTranslation.created_at.desc()).limit(limit).all()

        # examples = []
        # for item in results:
        #     examples.append({
        #         "id": item.id,
        #         "source_text": item.source_text,
        #         "translation": item.translation,
        #         "domain": item.domain,
        #         "section_type": item.section_type,
        #         "confidence_score": item.confidence_score,
        #         "similarity_score": None,
        #     })

        # return examples
