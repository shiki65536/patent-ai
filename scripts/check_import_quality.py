import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import PatentTranslation
from sqlalchemy import func

db = SessionLocal()

print("=" * 60)
print("Import Quality Check")
print("=" * 60)

# Check text lengths
lengths = db.query(
    func.avg(func.length(PatentTranslation.source_text)),
    func.avg(func.length(PatentTranslation.translation)),
    func.min(func.length(PatentTranslation.source_text)),
    func.max(func.length(PatentTranslation.source_text))
).first()

print(f"\nText Length Statistics:")
print(f"  Avg JP length: {lengths[0]:.0f} chars")
print(f"  Avg ZH length: {lengths[1]:.0f} chars")
print(f"  Min JP length: {lengths[2]} chars")
print(f"  Max JP length: {lengths[3]} chars")

# Check for potential issues
short = db.query(PatentTranslation).filter(
    func.length(PatentTranslation.source_text) < 200
).count()

print(f"\nPotential Issues:")
print(f"  Very short entries (<200 chars): {short}")

# Sample check
print(f"\nSample Entries:")
samples = db.query(PatentTranslation).limit(3).all()
for i, s in enumerate(samples, 1):
    print(f"\n{i}. {s.section_type} ({s.domain})")
    print(f"   JP: {s.source_text[:100]}...")
    print(f"   ZH: {s.translation[:100]}...")

db.close()