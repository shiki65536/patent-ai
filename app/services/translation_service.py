import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import PatentTranslation, TranslationRequest, TranslationResponse
from app.services.patent_translator import PatentTranslator
from app.services.terminology_manager import TerminologyManager
from app.services.translation_rag import TranslationRAG
from app.simple_auth import check_daily_cost_limit, record_estimated_cost

logger = logging.getLogger(__name__)


class TranslationService:
    """Main service orchestrating patent translation."""

    def __init__(self):
        self.translator = PatentTranslator()
        self.rag = TranslationRAG()
        self.term_manager = TerminologyManager()

    def translate(self, request: TranslationRequest, db: Session) -> TranslationResponse:
        logger.info("Starting translation for section: %s", request.section_type)
        start = time.time()

        examples = []
        if request.use_rag:
            examples = self.rag.retrieve_similar_translations(
                request.japanese_text,
                db,
                domain=request.domain,
                section_type=request.section_type,
                limit=request.num_examples,
            )
            logger.info("Retrieved %s similar examples", len(examples))

        terminology = self.term_manager.get_relevant_terms(
            request.japanese_text,
            db,
            domain=request.domain,
        )
        logger.info("Found %s relevant terms", len(terminology))

        translation, confidence, translation_metadata = self.translator.translate(
            request.japanese_text,
            section_type=request.section_type,
            domain=request.domain,
            examples=examples,
            terminology=terminology,
            provider=request.provider,
        )

        estimated_cost = translation_metadata.get("estimated_cost_usd", 0.0)
        check_daily_cost_limit(estimated_cost)
        record_estimated_cost(estimated_cost)

        translation_id = 0
        if settings.PERSIST_TRANSLATIONS:
            db_translation = PatentTranslation(
                source_text=request.japanese_text,
                source_language="japanese",
                translation=translation,
                target_language="traditional_chinese",
                patent_id=request.patent_id,
                section_type=request.section_type,
                domain=request.domain,
                confidence_score=confidence,
                terminology_matches=len(terminology),
                file_name=request.file_name,
                retrieved_examples=[example.get("id") for example in examples],
                translated_by=translation_metadata.get("provider", settings.LLM_PROVIDER),
            )

            db.add(db_translation)
            db.commit()
            db.refresh(db_translation)
            translation_id = db_translation.id

        latency_seconds = round(time.time() - start, 3)
        logger.info("Translation completed in %ss", latency_seconds)

        return TranslationResponse(
            translation_id=translation_id,
            translation=translation,
            confidence_score=confidence,
            retrieved_examples=examples,
            terminology_used=terminology,
            metadata={
                "section_type": request.section_type,
                "domain": request.domain,
                "examples_used": len(examples),
                "terms_matched": len(terminology),
                "latency_seconds": latency_seconds,
                **translation_metadata,
            },
            translated_at=datetime.utcnow(),
        )
