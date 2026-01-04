"""
Batch translate multiple PDF files
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def batch_translate(input_dir: str, output_dir: str, domain: str):
    """Translate all PDFs in a directory"""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find all PDFs
    pdf_files = list(input_path.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Import here to avoid circular import
    from scripts.translate_pdf import PDFTranslator
    
    translator = PDFTranslator()
    
    results = []
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        
        output_file = output_path / f"{pdf_file.stem}_translated.docx"
        
        try:
            result = translator.translate_pdf(
                str(pdf_file),
                str(output_file),
                domain=domain
            )
            results.append({
                'file': pdf_file.name,
                'status': 'success',
                'output': str(output_file),
                'stats': result['stats']
            })
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            results.append({
                'file': pdf_file.name,
                'status': 'failed',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("Batch Translation Summary")
    print("=" * 80)
    
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    print(f"Total files:    {len(pdf_files)}")
    print(f"Successful:     {successful}")
    print(f"Failed:         {failed}")
    
    # Save report
    import json
    report_file = output_path / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nReport saved: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='Batch translate PDFs')
    parser.add_argument('input_dir', help='Directory with PDF files')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--domain', '-d', default='semiconductor')
    
    args = parser.parse_args()
    
    batch_translate(args.input_dir, args.output_dir, args.domain)


if __name__ == "__main__":
    main()