"""
Import a single patent pair for testing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.utils.document_processor import DocumentProcessor, PatentSectionParser
from app.models import PatentTranslation

def import_single_pair(jp_file: str, zh_file: str):
    """Import single patent pair"""
    
    print(f"Japanese: {jp_file}")
    print(f"Chinese: {zh_file}")
    
    # Extract text
    processor = DocumentProcessor()
    jp_text = processor.extract_text(jp_file)
    zh_text = processor.extract_text(zh_file)
    
    print(f"\nExtracted text lengths:")
    print(f"  Japanese: {len(jp_text)} chars")
    print(f"  Chinese: {len(zh_text)} chars")
    
    # Parse sections
    parser = PatentSectionParser()
    jp_sections = parser.parse_sections(jp_text)
    zh_sections = parser.parse_sections(zh_text)
    
    print(f"\nFound sections:")
    print(f"  Japanese: {list(jp_sections.keys())}")
    print(f"  Chinese: {list(zh_sections.keys())}")
    
    # Import to database
    db = SessionLocal()
    imported = 0
    
    for section_name in jp_sections:
        if section_name in zh_sections:
            translation = PatentTranslation(
                source_text=jp_sections[section_name][:5000],
                translation=zh_sections[section_name][:5000],
                patent_id="test",
                section_type=section_name,
                domain="test",
                confidence_score=1.0,
                file_name=Path(jp_file).name,
                translated_by="human"
            )
            db.add(translation)
            imported += 1
            print(f"  ✓ Imported: {section_name}")
    
    db.commit()
    db.close()
    
    print(f"\n✓ Total imported: {imported} sections")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python import_single_pair.py <japanese_file> <chinese_file>")
        sys.exit(1)
    
    import_single_pair(sys.argv[1], sys.argv[2])