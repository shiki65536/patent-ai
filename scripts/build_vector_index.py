"""
Build vector index with proper error handling
"""
import sys
import os
from pathlib import Path

# Disable telemetry before any imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.vector_rag import VectorRAG
from app.models import PatentTranslation
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("Building Vector Index")
    print("=" * 60)
    
    # Check database first
    db = SessionLocal()
    total_in_db = db.query(PatentTranslation).count()
    
    print(f"\nTranslations in database: {total_in_db}")
    
    if total_in_db == 0:
        print("\n⚠️  No translations in database!")
        print("Please run: python scripts/import_patent_corpus.py")
        db.close()
        return
    
    # Initialize VectorRAG
    print("\nInitializing vector database...")
    try:
        vector_rag = VectorRAG()
    except Exception as e:
        print(f"\n✗ Failed to initialize VectorRAG: {e}")
        db.close()
        return
    
    # Check existing index
    existing = vector_rag.collection.count()
    print(f"Existing embeddings in index: {existing}")
    
    if existing >= total_in_db:
        print("\n✓ Index is already up to date!")
        response = input("Rebuild anyway? (yes/no): ")
        if response.lower() != 'yes':
            db.close()
            return
        
        # Clear existing
        print("Clearing existing index...")
        vector_rag.client.delete_collection("patent_translations")
        vector_rag = VectorRAG()
    
    # Build index
    print(f"\nIndexing {total_in_db} translations...")
    print("This may take several minutes...\n")
    
    try:
        indexed = vector_rag.build_index_from_db(db)
        
        print("\n" + "=" * 60)
        print("✓ Vector index built successfully!")
        print("=" * 60)
        print(f"  Total in database:    {total_in_db}")
        print(f"  Newly indexed:        {indexed}")
        print(f"  Total in index:       {vector_rag.collection.count()}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Index build failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
