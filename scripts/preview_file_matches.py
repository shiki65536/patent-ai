"""
Preview file matching without importing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.file_matcher import FileNameMatcher

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Preview file matching')
    parser.add_argument('japanese_dir', help='Directory with Japanese files')
    parser.add_argument('chinese_dir', help='Directory with Chinese files')
    
    args = parser.parse_args()
    
    jp_path = Path(args.japanese_dir)
    zh_path = Path(args.chinese_dir)
    
    print("=" * 80)
    print("File Matching Preview")
    print("=" * 80)
    
    pairs = FileNameMatcher.find_all_pairs(jp_path, zh_path)
    
    print(f"\nFound {len(pairs)} matched pairs:\n")
    
    for i, (jp_file, zh_file) in enumerate(pairs, 1):
        patent_id = FileNameMatcher.extract_patent_id(jp_file.name)
        print(f"{i:3}. [{patent_id}]")
        print(f"     JP: {jp_file.name}")
        print(f"     ZH: {zh_file.name}")
        print()
    
    # Check for unmatched files
    all_jp = [
        f for f in jp_path.glob("*")
        if f.suffix.lower() in ['.doc', '.docx', '.pdf']
        and FileNameMatcher.is_japanese_file(f.name)
    ]
    
    matched_jp = {jp for jp, zh in pairs}
    unmatched_jp = set(all_jp) - matched_jp
    
    if unmatched_jp:
        print("=" * 80)
        print(f"Unmatched Japanese files ({len(unmatched_jp)}):")
        print("=" * 80)
        for f in sorted(unmatched_jp):
            patent_id = FileNameMatcher.extract_patent_id(f.name)
            print(f"  [{patent_id or 'NO_ID'}] {f.name}")


if __name__ == "__main__":
    main()
