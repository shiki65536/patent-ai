import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json

def test_translation():
    """Test translation with different scenarios"""
    
    base_url = "http://localhost:8000/api/v1"
    
    test_cases = [
        {
            "name": "半導體製程 (應觸發術語)",
            "text": "半導体デバイスの製造工程では、ウエハに処理液を供給する。クーロン力により基板を保持する。",
            "domain": "semiconductor",
            "expected_terms": ["ウエハ", "クーロン力"]
        },
        {
            "name": "機械裝置",
            "text": "歯車を用いた伝達機構において、軸受によって回転を支持する。",
            "domain": "mechanical",
            "expected_terms": ["歯車", "軸受"]
        },
        {
            "name": "長文測試",
            "text": """
            本発明は、基板処理装置に関する。
            半導体デバイスの製造工程では、半導体ウエハ等の基板に処理液を供給することによって、
            たとえばレジスト膜等の除去対象物を基板から除去する技術が知られている。
            """,
            "domain": "semiconductor",
            "expected_terms": ["半導体ウエハ", "レジスト膜"]
        }
    ]
    
    print("=" * 80)
    print("Translation Quality Test")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}] {test['name']}")
        print(f"Input: {test['text'][:80]}...")
        
        # Test RAG first
        rag_response = requests.post(
            f"{base_url}/translate/test-rag",
            json={
                "japanese_text": test['text'],
                "domain": test['domain'],
                "section_type": "background",
                "use_rag": True,
                "num_examples": 3
            }
        )
        
        if rag_response.status_code == 200:
            rag_data = rag_response.json()
            print(f"\nRAG Status:")
            print(f"  Examples retrieved: {rag_data['rag_status']['examples_retrieved']}")
            print(f"  Terms matched: {rag_data['rag_status']['terms_matched']}")
            print(f"  Avg similarity: {rag_data['rag_status']['avg_similarity']:.3f}")
            
            if rag_data['terminology_found']:
                print(f"\n  Matched terms:")
                for term in rag_data['terminology_found'][:5]:
                    print(f"    {term['japanese_term']} → {term['chinese_term']}")
        
        # Full translation
        trans_response = requests.post(
            f"{base_url}/translate",
            json={
                "japanese_text": test['text'],
                "domain": test['domain'],
                "section_type": "background",
                "use_rag": True,
                "num_examples": 3
            }
        )
        
        if trans_response.status_code == 200:
            trans_data = trans_response.json()
            print(f"\nTranslation:")
            print(f"  {trans_data['translation'][:100]}...")
            print(f"  Confidence: {trans_data['confidence_score']:.2f}")
            print(f"  Examples used: {trans_data['metadata']['examples_used']}")
            print(f"  Terms matched: {trans_data['metadata']['terms_matched']}")
        else:
            print(f"  ✗ Translation failed: {trans_response.status_code}")
        
        print("-" * 80)

if __name__ == "__main__":
    test_translation()