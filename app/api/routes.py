from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.models import (
    TranslationRequest, TranslationResponse,
    TerminologyRequest, TerminologyResponse,
    PatentTranslation, TerminologyEntry, PatentTranslationOut
)
from app.services.translation_service import TranslationService
from app.services.terminology_manager import TerminologyManager
from app.database import get_db
from typing import List
import time
from app.services.vector_rag import VectorRAG
from sqlalchemy import func
from app.services.translation_rag import TranslationRAG

# Import auth function
from app.simple_auth import check_auth_and_rate_limit

router = APIRouter()

# Optional Prometheus metrics
try:
    from prometheus_client import Counter, Histogram
    PROM_ENABLED = True
    translation_counter = Counter('patent_translations_total', 'Total translations')
    translation_duration = Histogram('translation_duration_seconds', 'Translation time')
except ImportError:
    PROM_ENABLED = False


# ===== PUBLIC ENDPOINTS (No auth required) =====

@router.get("/health")
async def health_check():
    """Public health check endpoint"""
    return {
        "status": "healthy",
        "service": "patent-translation-ai",
        "version": "1.0.0",
        "features": ["translation", "rag", "terminology"]
    }


@router.get("/system/status")
async def system_status(db: Session = Depends(get_db)):
    """Public system status - no auth required"""
    
    # Database stats
    total_trans = db.query(PatentTranslation).count()
    total_terms = db.query(TerminologyEntry).count()
    used_terms = db.query(TerminologyEntry).filter(
        TerminologyEntry.usage_count > 0
    ).count()
    
    # Domain distribution
    domains = db.query(
        PatentTranslation.domain,
        func.count(PatentTranslation.id)
    ).group_by(PatentTranslation.domain).all()
    
    # Vector index status
    try:
        vector_rag = VectorRAG()
        vector_count = vector_rag.collection.count()
        vector_coverage = vector_count / total_trans * 100 if total_trans > 0 else 0
    except:
        vector_count = 0
        vector_coverage = 0
    
    return {
        "status": "operational",
        "database": {
            "total_translations": total_trans,
            "total_terminology": total_terms,
            "terminology_usage_rate": f"{used_terms/total_terms*100:.1f}%" if total_terms > 0 else "0%",
            "domain_distribution": {d: c for d, c in domains}
        },
        "vector_search": {
            "indexed_embeddings": vector_count,
            "coverage": f"{vector_coverage:.1f}%",
            "status": "healthy" if vector_coverage > 95 else "needs_reindex"
        },
        "features": {
            "rag": True,
            "terminology": True,
            "multi_domain": True,
            "vector_search": vector_count > 0
        }
    }


# ===== PROTECTED ENDPOINTS (Require auth + rate limit) =====

@router.post("/translate", response_model=TranslationResponse)
async def translate_patent(
    request: TranslationRequest,
    req: Request,  # Add Request for auth check
    db: Session = Depends(get_db)
):
    """
    Translate Japanese patent text to Traditional Chinese
    
    Protected endpoint: requires API key (if configured) and rate limiting
    
    - **japanese_text**: Source text in Japanese
    - **section_type**: Type of section (claim, description, abstract, background)
    - **domain**: Technical domain (semiconductor, mechanical)
    - **use_rag**: Enable RAG retrieval (default: True)
    - **num_examples**: Number of examples to retrieve (default: 3)
    """
    # Check authentication and rate limit
    check_auth_and_rate_limit(req)
    
    start_time = time.time()
    if PROM_ENABLED:
        translation_counter.inc()
    
    try:
        service = TranslationService()
        result = service.translate(request, db)
        
        duration = time.time() - start_time
        if PROM_ENABLED:
            translation_duration.observe(duration)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/translate/test-rag")
async def test_rag_only(
    request: TranslationRequest,
    req: Request,  # Add Request for auth check
    db: Session = Depends(get_db)
):
    """
    Test RAG retrieval only (no actual translation)
    Useful for debugging RAG performance
    
    Protected endpoint
    """
    # Check authentication and rate limit
    check_auth_and_rate_limit(req)
    
    rag = TranslationRAG()
    term_manager = TerminologyManager()
    
    # Retrieve examples
    examples = rag.retrieve_similar_translations(
        request.japanese_text,
        db,
        domain=request.domain,
        section_type=request.section_type,
        limit=request.num_examples
    )
    
    # Get terminology
    terminology = term_manager.get_relevant_terms(
        request.japanese_text,
        db,
        domain=request.domain
    )
    
    return {
        "query": request.japanese_text,
        "retrieved_examples": examples,
        "terminology_found": terminology,
        "rag_status": {
            "examples_retrieved": len(examples),
            "terms_matched": len(terminology),
            "avg_similarity": sum(ex.get('similarity_score', 0) for ex in examples) / len(examples) if examples else 0
        }
    }


@router.get("/translations/{translation_id}", response_model=PatentTranslationOut)
async def get_translation(
    translation_id: int,
    req: Request,  # Add for auth
    db: Session = Depends(get_db)
):
    """Get translation by ID - Protected endpoint"""
    check_auth_and_rate_limit(req)
    
    translation = db.query(PatentTranslation).filter(
        PatentTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    return translation


@router.get("/translations", response_model=List[PatentTranslationOut])
async def list_translations(
    req: Request,  # Add for auth
    domain: str = None,
    section_type: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List recent translations - Protected endpoint"""
    check_auth_and_rate_limit(req)
    
    query = db.query(PatentTranslation)
    
    if domain:
        query = query.filter(PatentTranslation.domain == domain)
    if section_type:
        query = query.filter(PatentTranslation.section_type == section_type)
    
    translations = query.order_by(
        PatentTranslation.created_at.desc()
    ).limit(limit).all()
    
    return translations


# ===== Terminology Endpoints (Protected) =====

@router.post("/terminology", response_model=TerminologyResponse)
async def add_terminology(
    request: TerminologyRequest,
    req: Request,  # Add for auth
    db: Session = Depends(get_db)
):
    """Add new terminology entry - Protected endpoint"""
    check_auth_and_rate_limit(req)
    
    try:
        manager = TerminologyManager()
        term = manager.add_term(
            request.japanese_term,
            request.chinese_term,
            request.domain,
            db,
            notes=request.notes
        )
        
        return TerminologyResponse(
            id=term.id,
            japanese_term=term.japanese_term,
            chinese_term=term.chinese_term,
            domain=term.domain,
            usage_count=term.usage_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add terminology: {str(e)}"
        )


@router.get("/terminology", response_model=List[TerminologyResponse])
async def list_terminology(
    domain: str = None,
    search: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List terminology entries - Public for read access"""
    
    query = db.query(TerminologyEntry)
    
    if domain:
        query = query.filter(TerminologyEntry.domain == domain)
    if search:
        query = query.filter(
            (TerminologyEntry.japanese_term.contains(search)) |
            (TerminologyEntry.chinese_term.contains(search))
        )
    
    terms = query.order_by(
        TerminologyEntry.usage_count.desc()
    ).limit(limit).all()
    
    return [
        TerminologyResponse(
            id=t.id,
            japanese_term=t.japanese_term,
            chinese_term=t.chinese_term,
            domain=t.domain,
            usage_count=t.usage_count
        )
        for t in terms
    ]


@router.get("/terminology/search")
async def search_terminology(
    query: str,
    language: str = "japanese",
    domain: str = None,
    db: Session = Depends(get_db)
):
    """Search terminology - Public for read access"""
    
    db_query = db.query(TerminologyEntry)
    
    if language == "japanese":
        db_query = db_query.filter(TerminologyEntry.japanese_term.contains(query))
    else:
        db_query = db_query.filter(TerminologyEntry.chinese_term.contains(query))
    
    if domain:
        db_query = db_query.filter(TerminologyEntry.domain == domain)
    
    results = db_query.order_by(TerminologyEntry.usage_count.desc()).limit(20).all()
    
    return [
        {
            "japanese": t.japanese_term,
            "chinese": t.chinese_term,
            "domain": t.domain,
            "usage_count": t.usage_count,
            "verified": t.verified == 1
        }
        for t in results
    ]


@router.delete("/terminology/{term_id}")
async def delete_terminology(
    term_id: int,
    req: Request,  # Add for auth
    db: Session = Depends(get_db)
):
    """Delete terminology entry - Protected endpoint"""
    check_auth_and_rate_limit(req)
    
    term = db.query(TerminologyEntry).filter(
        TerminologyEntry.id == term_id
    ).first()
    
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    
    db.delete(term)
    db.commit()
    
    return {"message": "Terminology deleted successfully"}


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics - Public endpoint"""
    
    total_translations = db.query(PatentTranslation).count()
    total_terms = db.query(TerminologyEntry).count()
    
    # Count by domain
    domains = db.query(
        PatentTranslation.domain,
        func.count(PatentTranslation.id)
    ).group_by(PatentTranslation.domain).all()
    
    return {
        "total_translations": total_translations,
        "total_terminology_entries": total_terms,
        "translations_by_domain": {d: c for d, c in domains if d}
    }