"""
Test RAG retrieval
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.translation_rag import TranslationRAG

def main():
    print("=" * 60)
    print("Testing RAG Retrieval")
    print("=" * 60)
    
    # Test query
    test_query = "半導体装置の製造方法に関する"
    
    print(f"\nQuery: {test_query}")
    print("\nSearching for similar translations...")
    
    db = SessionLocal()
    rag = TranslationRAG()
    
    try:
        results = rag.retrieve_similar_translations(
            test_query,
            db,
            domain="semiconductor",
            limit=3
        )
        
        print(f"\nFound {len(results)} similar translations:")
        
        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"ID: {result['id']}")
            print(f"Similarity: {result.get('similarity_score', 0):.3f}")
            print(f"Section: {result['section_type']}")
            print(f"Source: {result['source_text'][:100]}...")
            print(f"Translation: {result['translation'][:100]}...")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()