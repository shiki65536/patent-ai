"""
Import patent corpus - COMPLETE VERSION
"""
import sys
import os
from pathlib import Path
from typing import List, Tuple
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import PatentTranslation
from app.utils.document_processor import DocumentProcessor, PatentSectionParser
from app.utils.file_matcher import FileNameMatcher
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CorpusImporter:
    """Import patent corpus with robust error handling"""
    
    def __init__(self, db: Session):
        self.db = db
        self.doc_processor = DocumentProcessor()
        self.section_parser = PatentSectionParser()
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'successful': 0,
            'skipped_ocr': 0,
            'skipped_error': 0,
            'skipped_no_match': 0,
            'sections_imported': 0,
            'claims_imported': 0,
        }
    
    def import_patent_pair(
        self,
        japanese_file: str,
        chinese_file: str,
        domain: str = None,
        patent_id: str = None
    ) -> int:
        """Import a Japanese-Chinese patent pair"""
        
        self.stats['total_files'] += 1
        logger.info(f"[{self.stats['total_files']}] Processing: {Path(japanese_file).name}")
        
        # Extract text
        jp_text = self.doc_processor.extract_text(japanese_file)
        if jp_text is None:
            logger.warning(f"  ⚠ Skipped (OCR needed or error): {Path(japanese_file).name}")
            self.stats['skipped_ocr'] += 1
            return 0
        
        zh_text = self.doc_processor.extract_text(chinese_file)
        if zh_text is None:
            logger.warning(f"  ⚠ Skipped Chinese file: {Path(chinese_file).name}")
            self.stats['skipped_error'] += 1
            return 0
        
        # Clean text (remove diagrams)
        jp_text = self.doc_processor.clean_text(jp_text)
        zh_text = self.doc_processor.clean_text(zh_text)
        
        logger.info(f"  Extracted: JP={len(jp_text)} chars, ZH={len(zh_text)} chars")
        
        # Parse sections
        jp_sections = self.section_parser.parse_sections(jp_text, 'japanese')
        zh_sections = self.section_parser.parse_sections(zh_text, 'chinese')
        
        logger.info(f"  Sections: JP={len(jp_sections)}, ZH={len(zh_sections)}")
        logger.info(f"  JP claims? {'claims' in jp_sections} len={len(jp_sections.get('claims', ''))}")
        logger.info(f"  ZH claims? {'claims' in zh_sections} len={len(zh_sections.get('claims', ''))}")

        
        if not jp_sections or not zh_sections:
            logger.warning(f"  ⚠ No sections found")
            self.stats['skipped_error'] += 1
            return 0
        
        # Align and import sections
        aligned = self.section_parser.align_sections(jp_sections, zh_sections)
        
        imported = 0
        patent_id = patent_id or Path(japanese_file).stem
        
        for section_name, jp_content, zh_content in aligned:
            # Skip if content too short
            if len(jp_content) < 100 or len(zh_content) < 100:
                continue
            
            # Truncate if too long
            jp_content = jp_content[:10000]
            zh_content = zh_content[:10000]
            
            translation = PatentTranslation(
                source_text=jp_content,
                translation=zh_content,
                patent_id=patent_id,
                section_type=section_name,
                domain=domain or self._detect_domain(jp_content),
                confidence_score=1.0,
                file_name=Path(japanese_file).name,
                translated_by="human"
            )
            
            self.db.add(translation)
            imported += 1
            self.stats['sections_imported'] += 1
        
        # Handle claims separately
        if 'claims' in jp_sections and 'claims' in zh_sections:
            jp_claims = self.section_parser.extract_claims(jp_sections['claims'])
            zh_claims = self.section_parser.extract_claims(zh_sections['claims'])
            
            for jp_claim in jp_claims:
                matching_zh = next(
                    (c for c in zh_claims if c['number'] == jp_claim['number']),
                    None
                )
                
                if matching_zh:
                    translation = PatentTranslation(
                        source_text=jp_claim['text'][:10000],
                        translation=matching_zh['text'][:10000],
                        patent_id=patent_id,
                        section_type=f"claim_{jp_claim['number']}",
                        domain=domain,
                        confidence_score=1.0,
                        file_name=Path(japanese_file).name,
                        translated_by="human"
                    )
                    self.db.add(translation)
                    imported += 1
                    self.stats['claims_imported'] += 1
        
        self.db.commit()
        
        if imported > 0:
            logger.info(f"  ✓ Imported {imported} entries")
            self.stats['successful'] += 1
        else:
            logger.warning(f"  ⚠ No content imported")
        
        return imported
    
    def _detect_domain(self, text: str) -> str:
        """Detect domain from text"""
        semiconductor_kw = ["半導体", "トランジスタ", "ウェハ", "ウエハ", "集積回路", "MOSFET"]
        mechanical_kw = ["機械", "歯車", "軸受", "ベアリング", "モータ"]
        
        text_sample = text[:2000]
        semi_count = sum(1 for kw in semiconductor_kw if kw in text_sample)
        mech_count = sum(1 for kw in mechanical_kw if kw in text_sample)
        
        if semi_count > mech_count and semi_count > 0:
            return "semiconductor"
        elif mech_count > 0:
            return "mechanical"
        return "general"
    
    def import_from_directory(
        self,
        japanese_dir: str,
        chinese_dir: str,
        domain: str = None
    ) -> dict:
        """Import all patent pairs from directories"""
        
        jp_path = Path(japanese_dir)
        zh_path = Path(chinese_dir)
        
        # Use smart matcher
        pairs = FileNameMatcher.find_all_pairs(jp_path, zh_path)
        
        logger.info(f"Found {len(pairs)} matched pairs")
        
        for jp_file, zh_file in pairs:
            try:
                self.import_patent_pair(
                    str(jp_file),
                    str(zh_file),
                    domain=domain,
                    patent_id=FileNameMatcher.extract_patent_id(jp_file.name)
                )
            except Exception as e:
                logger.error(f"✗ Error processing {jp_file.name}: {e}")
                self.stats['skipped_error'] += 1
        
        return self.stats
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 80)
        print("Import Summary")
        print("=" * 80)
        print(f"Total files processed:    {self.stats['total_files']}")
        print(f"Successfully imported:    {self.stats['successful']}")
        print(f"Skipped (OCR needed):     {self.stats['skipped_ocr']}")
        print(f"Skipped (errors):         {self.stats['skipped_error']}")
        print(f"Skipped (no match):       {self.stats['skipped_no_match']}")
        print(f"\nSections imported:        {self.stats['sections_imported']}")
        print(f"Claims imported:          {self.stats['claims_imported']}")
        print(f"Total entries:            {self.stats['sections_imported'] + self.stats['claims_imported']}")
        print("=" * 80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import patent translation corpus')
    parser.add_argument('japanese_dir', help='Directory with Japanese files')
    parser.add_argument('chinese_dir', help='Directory with Chinese files')
    parser.add_argument('--domain', choices=['semiconductor', 'mechanical', 'general'],
                       help='Patent domain (optional, will auto-detect if not specified)')
    parser.add_argument('--preview', action='store_true',
                       help='Preview file matching without importing')
    
    args = parser.parse_args()
    
    # Preview mode
    if args.preview:
        print("=" * 80)
        print("File Matching Preview")
        print("=" * 80)
        
        jp_path = Path(args.japanese_dir)
        zh_path = Path(args.chinese_dir)
        
        pairs = FileNameMatcher.find_all_pairs(jp_path, zh_path)
        
        print(f"\nFound {len(pairs)} matched pairs:\n")
        
        for i, (jp_file, zh_file) in enumerate(pairs, 1):
            patent_id = FileNameMatcher.extract_patent_id(jp_file.name)
            print(f"{i:3}. [{patent_id}]")
            print(f"     JP: {jp_file.name}")
            print(f"     ZH: {zh_file.name}")
            print()
        
        return
    
    # Import mode
    print("=" * 80)
    print("Patent Translation Corpus Import")
    print("=" * 80)
    
    db = SessionLocal()
    importer = CorpusImporter(db)
    
    try:
        importer.import_from_directory(
            args.japanese_dir,
            args.chinese_dir,
            domain=args.domain
        )
        
        importer.print_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Import interrupted by user")
        importer.print_summary()
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()