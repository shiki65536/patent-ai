"""
Vector-based RAG with Chroma - All compatibility issues fixed
"""
import os
import sys

# CRITICAL: Disable telemetry BEFORE importing chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Suppress Chroma warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*telemetry.*')

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models import PatentTranslation
import logging

logger = logging.getLogger(__name__)

class VectorRAG:
    """Vector-based Retrieval Augmented Generation"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize VectorRAG with Chroma
        
        Uses:
        - Chroma 0.4.22+ (compatible with Pydantic 2)
        - NumPy <2 (for compatibility)
        - Telemetry completely disabled
        """
        try:
            # Use new PersistentClient API (Pydantic 2 compatible)
            self.client = chromadb.PersistentClient(path=persist_directory)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="patent_translations",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize embedding model (multilingual)
            logger.info("Loading multilingual embedding model...")
            self.embedding_model = SentenceTransformer(
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                device='cpu'  # Force CPU to avoid GPU issues
            )
            
            current_count = self.collection.count()
            logger.info(f"VectorRAG initialized: {current_count} embeddings in index")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorRAG: {e}")
            raise
    
    def add_translation(
        self,
        translation_id: int,
        source_text: str,
        translation_text: str,
        metadata: Dict
    ):
        """Add translation to vector database"""
        
        try:
            # Create embedding from source text
            embedding = self.embedding_model.encode(
                source_text,
                convert_to_numpy=True,
                show_progress_bar=False
            ).tolist()
            
            # Prepare metadata (Chroma requires all values to be simple types)
            safe_metadata = {
                'translation_id': str(translation_id),
                'translation': translation_text[:500],
                'section_type': metadata.get('section_type', '') or '',
                'domain': metadata.get('domain', '') or '',
                'patent_id': metadata.get('patent_id', '') or ''
            }
            
            # Add to Chroma
            self.collection.add(
                embeddings=[embedding],
                documents=[source_text[:1000]],  # Store preview
                metadatas=[safe_metadata],
                ids=[f"trans_{translation_id}"]
            )
            
        except Exception as e:
            logger.error(f"Error adding translation {translation_id}: {e}")
            raise
    
    def search_similar(
        self,
        query_text: str,
        domain: Optional[str] = None,
        section_type: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict]:
        """Search for similar translations using vector similarity"""
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode(
                query_text,
                convert_to_numpy=True,
                show_progress_bar=False
            ).tolist()
            
            # Build where filter
            where_filter = {}
            if domain:
                where_filter['domain'] = domain
            if section_type:
                where_filter['section_type'] = section_type
            
            # Query Chroma
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None
            )
            
            # Format results
            similar_translations = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    similar_translations.append({
                        'id': int(results['metadatas'][0][i]['translation_id']),
                        'source_text': results['documents'][0][i],
                        'translation': results['metadatas'][0][i]['translation'],
                        'similarity_score': 1 - results['distances'][0][i],
                        'domain': results['metadatas'][0][i]['domain'],
                        'section_type': results['metadatas'][0][i]['section_type']
                    })
            
            return similar_translations
            
        except Exception as e:
            logger.error(f"Error searching similar translations: {e}")
            return []
    
    def build_index_from_db(self, db: Session, batch_size: int = 100):
        """Build vector index from existing database translations"""
        
        logger.info("Building vector index from database...")
        
        # Get total count
        total = db.query(PatentTranslation).count()
        logger.info(f"Found {total} translations to index")
        
        if total == 0:
            logger.warning("No translations in database to index!")
            return 0
        
        # Process in batches
        indexed = 0
        offset = 0
        errors = 0
        
        while offset < total:
            batch = db.query(PatentTranslation).offset(offset).limit(batch_size).all()
            
            for translation in batch:
                try:
                    # Skip if already indexed
                    existing = self.collection.get(ids=[f"trans_{translation.id}"])
                    if existing['ids']:
                        offset += 1
                        continue
                    
                    self.add_translation(
                        translation_id=translation.id,
                        source_text=translation.source_text,
                        translation_text=translation.translation,
                        metadata={
                            'section_type': translation.section_type or '',
                            'domain': translation.domain or '',
                            'patent_id': translation.patent_id or ''
                        }
                    )
                    indexed += 1
                    
                    if indexed % 50 == 0:
                        logger.info(f"Indexed {indexed}/{total} translations...")
                
                except Exception as e:
                    logger.error(f"Error indexing translation {translation.id}: {e}")
                    errors += 1
            
            offset += batch_size
        
        logger.info(f"✓ Indexing complete: {indexed} new, {errors} errors")
        return indexed
