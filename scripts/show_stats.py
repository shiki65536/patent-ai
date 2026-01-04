import sys
from sqlalchemy import func

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import PatentTranslation, TerminologyEntry

db = SessionLocal()

print("=" * 60)
print("Database Statistics")
print("=" * 60)

# Translations
total = db.query(PatentTranslation).count()
print(f"\nTotal translations: {total}")

# By domain
domains = db.query(
    PatentTranslation.domain,
    func.count(PatentTranslation.id)
).group_by(PatentTranslation.domain).all()

print("\nBy domain:")
for domain, count in domains:
    print(f"  {domain or 'unknown'}: {count}")

# By section
sections = db.query(
    PatentTranslation.section_type,
    func.count(PatentTranslation.id)
).group_by(PatentTranslation.section_type).all()

print("\nBy section:")
for section, count in sections[:10]:
    print(f"  {section}: {count}")

# Terminology
term_count = db.query(TerminologyEntry).count()
print(f"\nTerminology entries: {term_count}")

db.close()