import numpy as np
from typing import Optional, Tuple, Dict, List
from sqlalchemy.orm import Session
from app.models import FaceEmbedding
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # In-memory cache for fast lookups
        # Format: { person_id: numpy_array_embedding }
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_loaded = False

    def load_cache(self, db: Session):
        """Load all embeddings from database into memory cache"""
        if self._cache_loaded:
            return
            
        logger.info("Loading face embeddings into memory cache...")
        all_embeddings = db.query(FaceEmbedding).all()
        
        self._cache.clear()
        for record in all_embeddings:
            try:
                emb = np.frombuffer(record.embedding, dtype=np.float32)
                self._cache[record.person_id] = emb
            except Exception as e:
                logger.error(f"Failed to load embedding for {record.person_id}: {str(e)}")
                
        self._cache_loaded = True
        logger.info(f"Loaded {len(self._cache)} embeddings into cache.")

    def register_face(self, db: Session, person_id: str, embedding: np.ndarray) -> bool:
        """Save or update face embedding in database and cache"""
        # Convert numpy array to bytes for storage
        # Ensure it's float32 for consistency
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        db_record = db.query(FaceEmbedding).filter(FaceEmbedding.person_id == person_id).first()
        
        if db_record:
            db_record.embedding = embedding_bytes
        else:
            db_record = FaceEmbedding(person_id=person_id, embedding=embedding_bytes)
            db.add(db_record)
            
        db.commit()
        
        # Update cache
        self._cache[person_id] = embedding.astype(np.float32)
        return True

    def delete_face(self, db: Session, person_id: str) -> bool:
        """Delete a face embedding from database and cache"""
        db_record = db.query(FaceEmbedding).filter(FaceEmbedding.person_id == person_id).first()
        if db_record:
            db.delete(db_record)
            db.commit()
            
            # Remove from cache
            if person_id in self._cache:
                del self._cache[person_id]
            return True
        return False

    def get_total_faces(self, db: Session) -> int:
        """Get total number of registered faces"""
        # Return from cache if loaded, otherwise query db
        if self._cache_loaded:
            return len(self._cache)
        return db.query(FaceEmbedding).count()

    def find_best_match(self, db: Session, query_embedding: np.ndarray) -> Tuple[bool, Optional[str], float]:
        """
        Compare query_embedding against all registered faces using cosine similarity.
        Returns: (is_match, person_id, confidence_percentage)
        """
        # Ensure cache is loaded
        self.load_cache(db)
        
        if not self._cache:
            return False, None, 0.0

        best_score = -1.0
        best_person_id = None
        
        # Convert query embedding to float32 for consistent comparison
        query_emb = query_embedding.astype(np.float32)
        
        for person_id, stored_emb in self._cache.items():
            # Compute cosine similarity
            # InsightFace normed_embedding is already L2 normalized, but we re-normalize just in case
            norm_q = np.linalg.norm(query_emb)
            norm_s = np.linalg.norm(stored_emb)
            
            if norm_q == 0 or norm_s == 0:
                continue
                
            sim = np.dot(query_emb, stored_emb) / (norm_q * norm_s)
            
            if sim > best_score:
                best_score = float(sim)
                best_person_id = person_id

        # Check threshold
        if best_score >= settings.MATCH_THRESHOLD:
            # Convert similarity (-1 to 1) to percentage (0 to 100) roughly
            # Assuming threshold > 0 (e.g. 0.55), we can just scale based on max 1.0
            confidence = round(best_score * 100, 2)
            # Cap at 100 just in case of float precision issues
            confidence = min(confidence, 100.0)
            return True, best_person_id, confidence
            
        return False, None, 0.0

    def compare_embeddings(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Helper to compute cosine similarity between two embeddings."""
        norm_1 = np.linalg.norm(emb1)
        norm_2 = np.linalg.norm(emb2)
        if norm_1 == 0 or norm_2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm_1 * norm_2))

embedding_service = EmbeddingService()
