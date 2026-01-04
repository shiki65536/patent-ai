import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import PatentTranslation, TerminologyEntry
from sqlalchemy import func

db = SessionLocal()

print("=" * 80)
print("Patent Translation System - Status Report")
print("=" * 80)

# 1. Corpus Statistics
total_trans = db.query(PatentTranslation).count()
unique_patents = db.query(func.count(func.distinct(PatentTranslation.patent_id))).scalar()

print(f"\n📚 Translation Corpus:")
print(f"   Total entries:        {total_trans}")
print(f"   Unique patents:       {unique_patents}")
print(f"   Avg per patent:       {total_trans/unique_patents:.1f}")

# By domain
domains = db.query(
    PatentTranslation.domain,
    func.count(PatentTranslation.id)
).group_by(PatentTranslation.domain).all()

print(f"\n   By Domain:")
for domain, count in domains:
    pct = count/total_trans*100
    print(f"     {domain or 'unknown':15s}: {count:4d} ({pct:5.1f}%)")

# By section type
sections = db.query(
    PatentTranslation.section_type,
    func.count(PatentTranslation.id)
).group_by(PatentTranslation.section_type).all()

print(f"\n   Top Section Types:")
for section, count in sorted(sections, key=lambda x: x[1], reverse=True)[:10]:
    print(f"     {section:20s}: {count:4d}")

# 2. Terminology
total_terms = db.query(TerminologyEntry).count()
verified_terms = db.query(TerminologyEntry).filter(TerminologyEntry.verified == 1).count()

print(f"\n📖 Terminology Database:")
print(f"   Total entries:        {total_terms}")
print(f"   Verified:             {verified_terms}")
print(f"   Unverified:           {total_terms - verified_terms}")

term_domains = db.query(
    TerminologyEntry.domain,
    func.count(TerminologyEntry.id)
).group_by(TerminologyEntry.domain).all()

print(f"\n   By Domain:")
for domain, count in term_domains:
    print(f"     {domain:15s}: {count:4d}")

# Most used terms
top_terms = db.query(TerminologyEntry).order_by(
    TerminologyEntry.usage_count.desc()
).limit(10).all()

print(f"\n   Most Used Terms:")
for i, term in enumerate(top_terms, 1):
    print(f"     {i:2d}. {term.japanese_term} → {term.chinese_term} ({term.usage_count} uses)")

# 3. Quality Metrics
avg_lengths = db.query(
    func.avg(func.length(PatentTranslation.source_text)),
    func.avg(func.length(PatentTranslation.translation))
).first()

print(f"\n📏 Quality Metrics:")
print(f"   Avg JP length:        {avg_lengths[0]:.0f} chars")
print(f"   Avg ZH length:        {avg_lengths[1]:.0f} chars")
print(f"   Length ratio:         {avg_lengths[1]/avg_lengths[0]:.2f}")

# 4. System Status
try:
    from app.services.vector_rag import VectorRAG
    vector_rag = VectorRAG()
    vector_count = vector_rag.collection.count()
    print(f"\n🔍 Vector Search:")
    print(f"   Indexed embeddings:   {vector_count}")
    print(f"   Coverage:             {vector_count/total_trans*100:.1f}%")
except Exception as e:
    print(f"\n🔍 Vector Search:")
    print(f"   Status:               Not initialized")

print("\n" + "=" * 80)

db.close()
