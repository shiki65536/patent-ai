from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import TerminologyEntry


class TerminologyManager:
    """Manage patent terminology database."""

    def get_relevant_terms(
        self,
        japanese_text: str,
        db: Session,
        domain: Optional[str] = None,
    ) -> List[Dict]:
        """Get terminology entries that appear in the text."""

        query = db.query(TerminologyEntry)
        if domain:
            query = query.filter(
                (TerminologyEntry.domain == domain) |
                (TerminologyEntry.domain == "general")
            )

        terms = query.all()
        relevant = []

        for term in terms:
            if term.japanese_term in japanese_text:
                relevant.append({
                    "japanese_term": term.japanese_term,
                    "chinese_term": term.chinese_term,
                    "domain": term.domain,
                })

                if settings.PERSIST_TRANSLATIONS:
                    term.usage_count += 1
                    term.last_used = datetime.utcnow()

        if settings.PERSIST_TRANSLATIONS:
            db.commit()

        return relevant

    def add_term(
        self,
        japanese_term: str,
        chinese_term: str,
        domain: str,
        db: Session,
        notes: Optional[str] = None,
    ) -> TerminologyEntry:
        """Add new terminology entry."""

        existing = db.query(TerminologyEntry).filter(
            TerminologyEntry.japanese_term == japanese_term
        ).first()

        if existing:
            existing.chinese_term = chinese_term
            existing.domain = domain
            existing.notes = notes
            db.commit()
            return existing

        term = TerminologyEntry(
            japanese_term=japanese_term,
            chinese_term=chinese_term,
            domain=domain,
            notes=notes,
        )
        db.add(term)
        db.commit()
        db.refresh(term)

        return term
