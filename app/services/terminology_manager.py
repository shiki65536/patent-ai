from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models import TerminologyEntry
from datetime import datetime

class TerminologyManager:
    """Manage patent terminology database"""
    
    def get_relevant_terms(
        self,
        japanese_text: str,
        db: Session,
        domain: Optional[str] = None
    ) -> List[Dict]:
        """Get terminology entries that appear in the text"""
        
        # Get all terms (or filter by domain)
        query = db.query(TerminologyEntry)
        if domain:
            query = query.filter(
                (TerminologyEntry.domain == domain) | 
                (TerminologyEntry.domain == "general")
            )
        
        terms = query.all()
        
        # Find terms that appear in text
        relevant = []
        for term in terms:
            if term.japanese_term in japanese_text:
                relevant.append({
                    'japanese_term': term.japanese_term,
                    'chinese_term': term.chinese_term,
                    'domain': term.domain
                })
                
                # Update usage stats
                term.usage_count += 1
                term.last_used = datetime.utcnow()
        
        db.commit()
        return relevant
    
    def add_term(
        self,
        japanese_term: str,
        chinese_term: str,
        domain: str,
        db: Session,
        notes: Optional[str] = None
    ) -> TerminologyEntry:
        """Add new terminology entry"""
        
        # Check if exists
        existing = db.query(TerminologyEntry).filter(
            TerminologyEntry.japanese_term == japanese_term
        ).first()
        
        if existing:
            # Update existing
            existing.chinese_term = chinese_term
            existing.domain = domain
            existing.notes = notes
            db.commit()
            return existing
        
        # Create new
        term = TerminologyEntry(
            japanese_term=japanese_term,
            chinese_term=chinese_term,
            domain=domain,
            notes=notes
        )
        db.add(term)
        db.commit()
        db.refresh(term)
        
        return term