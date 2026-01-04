from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.sql import func
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from app.db_base import Base

# ===== Database Models =====

class PatentTranslation(Base):
    """Database model for patent translations"""
    __tablename__ = "patent_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Source
    source_text = Column(Text, nullable=False)
    source_language = Column(String, default="japanese")
    
    # Translation
    translation = Column(Text, nullable=False)
    target_language = Column(String, default="traditional_chinese")
    
    # Metadata
    patent_id = Column(String, index=True)
    section_type = Column(String)  # claim, description, abstract, background
    domain = Column(String, index=True)  # semiconductor, mechanical
    
    # Quality metrics
    confidence_score = Column(Float)
    terminology_matches = Column(Integer, default=0)
    
    # Source info
    file_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    translated_by = Column(String, default="claude-ai")
    
    # Reference info
    retrieved_examples = Column(JSON)  # Store which examples were used


class PatentTranslationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_text: str
    source_language: str
    translation: str
    target_language: str
    patent_id: Optional[str] = None
    section_type: Optional[str] = None
    domain: Optional[str] = None
    confidence_score: Optional[float] = None
    terminology_matches: int = 0
    file_name: Optional[str] = None
    retrieved_examples: Optional[dict] = None
    created_at: datetime
    translated_by: str


class TerminologyEntry(Base):
    """Terminology database"""
    __tablename__ = "terminology"
    
    id = Column(Integer, primary_key=True, index=True)
    
    japanese_term = Column(String, unique=True, index=True)
    chinese_term = Column(String)
    domain = Column(String, index=True)  # semiconductor, mechanical, general
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True))
    
    # Metadata
    added_by = Column(String, default="manual")
    verified = Column(Integer, default=0)  # 0=unverified, 1=verified
    notes = Column(Text)


# ===== Pydantic Schemas =====

class TranslationRequest(BaseModel):
    """Request for patent translation"""
    japanese_text: str
    section_type: Optional[str] = "general"  # claim, description, abstract
    domain: Optional[str] = None  # semiconductor, mechanical
    patent_id: Optional[str] = None
    file_name: Optional[str] = None
    use_rag: bool = True  # Use RAG retrieval
    num_examples: int = 3  # Number of examples to retrieve

class TranslationResponse(BaseModel):
    """Response with translation"""
    translation_id: int
    translation: str
    confidence_score: float
    retrieved_examples: List[Dict]
    terminology_used: List[Dict]
    metadata: Dict
    translated_at: datetime

class TerminologyRequest(BaseModel):
    """Add terminology entry"""
    japanese_term: str
    chinese_term: str
    domain: str = "general"
    notes: Optional[str] = None

class TerminologyResponse(BaseModel):
    """Terminology entry response"""
    id: int
    japanese_term: str
    chinese_term: str
    domain: str
    usage_count: int
