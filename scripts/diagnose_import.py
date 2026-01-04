import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.file_matcher import FileNameMatcher
from app.utils.document_processor import DocumentProcessor

# 1. Check file matching
print("=" * 60)
print("File Matching Diagnosis")
print("=" * 60)

jp_dir = Path("data/corpus/japanese")
zh_dir = Path("data/corpus/chinese")

if not jp_dir.exists():
    print(f"✗ Japanese directory not found: {jp_dir}")
    sys.exit(1)

if not zh_dir.exists():
    print(f"✗ Chinese directory not found: {zh_dir}")
    sys.exit(1)

pairs = FileNameMatcher.find_all_pairs(jp_dir, zh_dir)
print(f"\nFound {len(pairs)} matched pairs")

if len(pairs) == 0:
    print("\n⚠️  No matched pairs found!")
    print("\nJapanese files:")
    for f in sorted(jp_dir.glob("*")):
        if f.suffix.lower() in ['.doc', '.docx', '.pdf']:
            print(f"  {f.name}")
    
    print("\nChinese files:")
    for f in sorted(zh_dir.glob("*")):
        if f.suffix.lower() in ['.doc', '.docx', '.pdf']:
            print(f"  {f.name}")
    
    sys.exit(1)

# 2. Test document extraction on first pair
print("\n" + "=" * 60)
print("Document Extraction Test (First Pair)")
print("=" * 60)

jp_file, zh_file = pairs[0]
print(f"\nJP: {jp_file.name}")
print(f"ZH: {zh_file.name}")

processor = DocumentProcessor()

jp_text = processor.extract_text(str(jp_file))
if jp_text:
    print(f"\n✓ JP extracted: {len(jp_text)} chars")
    print(f"  Preview: {jp_text[:200]}...")
else:
    print(f"\n✗ JP extraction failed")

zh_text = processor.extract_text(str(zh_file))
if zh_text:
    print(f"\n✓ ZH extracted: {len(zh_text)} chars")
    print(f"  Preview: {zh_text[:200]}...")
else:
    print(f"\n✗ ZH extraction failed")

# 3. Test section parsing
if jp_text and zh_text:
    from app.utils.document_processor import PatentSectionParser
    
    print("\n" + "=" * 60)
    print("Section Parsing Test")
    print("=" * 60)
    
    parser = PatentSectionParser()
    
    jp_sections = parser.parse_sections(jp_text, 'japanese')
    zh_sections = parser.parse_sections(zh_text, 'chinese')
    
    print(f"\nJP sections: {list(jp_sections.keys())}")
    print(f"ZH sections: {list(zh_sections.keys())}")
    
    aligned = parser.align_sections(jp_sections, zh_sections)
    print(f"\nAligned sections: {len(aligned)}")
    
    for section, jp, zh in aligned:
        print(f"  {section}: JP={len(jp)}, ZH={len(zh)}")
