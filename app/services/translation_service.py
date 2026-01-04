from sqlalchemy.orm import Session
from app.models import (
    TranslationRequest, TranslationResponse, 
    PatentTranslation
)
from app.services.patent_translator import PatentTranslator
from app.services.translation_rag import TranslationRAG
from app.services.terminology_manager import TerminologyManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TranslationService:
    """Main service orchestrating patent translation"""
    
    def __init__(self):
        self.translator = PatentTranslator()
        self.rag = TranslationRAG()
        self.term_manager = TerminologyManager()
    
    def translate(
        self, 
        request: TranslationRequest, 
        db: Session
    ) -> TranslationResponse:
        """Perform complete patent translation with RAG"""
        
        logger.info(f"Starting translation for section: {request.section_type}")
        
        # 1. Retrieve similar examples (if RAG enabled)
        examples = []
        if request.use_rag:
            examples = self.rag.retrieve_similar_translations(
                request.japanese_text,
                db,
                domain=request.domain,
                section_type=request.section_type,
                limit=request.num_examples
            )
            logger.info(f"Retrieved {len(examples)} similar examples")
        
        # 2. Get relevant terminology
        terminology = self.term_manager.get_relevant_terms(
            request.japanese_text,
            db,
            domain=request.domain
        )
        logger.info(f"Found {len(terminology)} relevant terms")
        
        # 3. Perform translation
        translation, confidence = self.translator.translate(
            request.japanese_text,
            section_type=request.section_type,
            domain=request.domain,
            examples=examples,
            terminology=terminology
        )
        
        # 4. Store translation
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
            retrieved_examples=[ex.get('id') for ex in examples]
        )
        
        db.add(db_translation)
        db.commit()
        db.refresh(db_translation)
        
        logger.info(f"Translation completed with ID: {db_translation.id}")
        
        return TranslationResponse(
            translation_id=db_translation.id,
            translation=translation,
            confidence_score=confidence,
            retrieved_examples=examples,
            terminology_used=terminology,
            metadata={
                'section_type': request.section_type,
                'domain': request.domain,
                'examples_used': len(examples),
                'terms_matched': len(terminology)
            },
            translated_at=datetime.utcnow()
        )