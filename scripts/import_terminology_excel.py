"""
Import terminology from Excel file
"""
import sys
from pathlib import Path
import pandas as pd
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import TerminologyEntry
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TerminologyImporter:
    """Import terminology from Excel file"""
    
    def __init__(self, db):
        self.seen_jp = set()
        self.db = db
        self.stats = {
            'total_rows': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def import_from_excel(self, excel_file: str, domain_mapping: dict = None):
        """
        Import terminology from Excel
        
        Args:
            excel_file: Path to .xls or .xlsx file
            domain_mapping: Dict mapping 分類 to domain
                           e.g., {'靜電夾頭': 'semiconductor'}
        """
        logger.info(f"Reading Excel file: {excel_file}")
        
        try:
            # Read Excel (handles both .xls and .xlsx)
            df = pd.read_excel(excel_file)
            
            # Check required columns
            # required_cols = ['日文', '中文']
            # if not all(col in df.columns for col in required_cols):
            #     raise ValueError(f"Excel must contain columns: {required_cols}")
            
            # logger.info(f"Found {len(df)} rows")

            # Strategy for not unique
            df["日文"] = df["日文"].astype(str).str.strip()
            df["中文"] = df["中文"].astype(str).str.strip()

            # Drop obvious empties
            df = df[(df["日文"] != "nan") & (df["中文"] != "nan") & (df["日文"] != "") & (df["中文"] != "")]

            # Keep last occurrence of each JP term (you can change keep="first")
            df = df.drop_duplicates(subset=["日文"], keep="last")
            logger.info(f"After de-dup by 日文: {len(df)} rows")

            # Process each row
            for idx, row in df.iterrows():
                self.stats['total_rows'] += 1
                
                try:
                    self._import_term(row, domain_mapping)
                except Exception as e:
                    logger.error(f"Row {idx+2} error: {e}")
                    self.stats['errors'] += 1
            
            # Commit all changes
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            raise
    
    def _import_term(self, row, domain_mapping):
        """Import single terminology entry"""
        
        jp_term = str(row['日文']).strip()
        zh_term = str(row['中文']).strip()

        if jp_term in self.seen_jp:
            self.stats["skipped"] += 1
            return
        self.seen_jp.add(jp_term)
        
        # Skip invalid entries
        if not jp_term or jp_term == 'nan' or not zh_term or zh_term == 'nan':
            self.stats['skipped'] += 1
            return
        
        # Skip if too short (likely errors)
        if len(jp_term) < 2 or len(zh_term) < 2:
            self.stats['skipped'] += 1
            return
        
        # Determine domain
        domain = 'general'
        if '分類' in row and pd.notna(row['分類']):
            category = str(row['分類']).strip()
            if domain_mapping and category in domain_mapping:
                domain = domain_mapping[category]
            else:
                # Auto-detect based on category name
                domain = self._detect_domain_from_category(category)
        
        # Check if term exists
        existing = self.db.query(TerminologyEntry).filter(
            TerminologyEntry.japanese_term == jp_term
        ).first()
        
        if existing:
            # Update existing
            existing.chinese_term = zh_term
            existing.domain = domain
            existing.verified = 1  # Mark as verified
            if '案號' in row and pd.notna(row['案號']):
                existing.notes = f"案號: {row['案號']}"
            self.stats['updated'] += 1
        else:
            # Create new
            notes = f"案號: {row['案號']}" if '案號' in row and pd.notna(row['案號']) else None
            
            term = TerminologyEntry(
                japanese_term=jp_term,
                chinese_term=zh_term,
                domain=domain,
                verified=1,
                added_by='excel_import',
                notes=notes
            )
            self.db.add(term)
            self.stats['imported'] += 1
        
        if self.stats['total_rows'] % 100 == 0:
            logger.info(f"Processed {self.stats['total_rows']} rows...")
    
    def _detect_domain_from_category(self, category: str) -> str:
        """Auto-detect domain from category name"""
        
        semiconductor_keywords = [
            '半導体', '電子', '回路', '夾頭', 'チップ', 
            'ウェハ', 'プラズマ', '薄膜'
        ]
        
        mechanical_keywords = [
            '機械', '機構', '装置', '軸', 'ベアリング',
            '歯車', 'モータ'
        ]
        
        for kw in semiconductor_keywords:
            if kw in category:
                return 'semiconductor'
        
        for kw in mechanical_keywords:
            if kw in category:
                return 'mechanical'
        
        return 'general'
    
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 60)
        print("Terminology Import Summary")
        print("=" * 60)
        print(f"Total rows:       {self.stats['total_rows']}")
        print(f"New entries:      {self.stats['imported']}")
        print(f"Updated entries:  {self.stats['updated']}")
        print(f"Skipped:          {self.stats['skipped']}")
        print(f"Errors:           {self.stats['errors']}")
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import terminology from Excel')
    parser.add_argument('excel_file', help='Path to .xls or .xlsx file')
    parser.add_argument('--domain-map', help='JSON file with category to domain mapping')
    
    args = parser.parse_args()
    
    # Load domain mapping if provided
    domain_mapping = None
    if args.domain_map:
        import json
        with open(args.domain_map) as f:
            domain_mapping = json.load(f)
    
    db = SessionLocal()
    importer = TerminologyImporter(db)
    
    try:
        importer.import_from_excel(args.excel_file, domain_mapping)
        importer.print_summary()
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
