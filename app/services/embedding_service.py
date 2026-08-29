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
        # Format: { (admin_id, person_id): numpy_array_embedding }
        self._cache: Dict[Tuple[Optional[str], str], np.ndarray] = {}
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
                self._cache[(record.admin_id, record.person_id)] = emb
            except Exception as e:
                logger.error(f"Failed to load embedding for admin_id={record.admin_id}, person_id={record.person_id}: {str(e)}")
                
        self._cache_loaded = True
        logger.info(f"Loaded {len(self._cache)} embeddings into cache.")

    def register_face(self, db: Session, person_id: str, embedding: np.ndarray, admin_id: Optional[str] = None) -> bool:
        """Save or update face embedding in database and cache under optional admin_id"""
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        query = db.query(FaceEmbedding).filter(FaceEmbedding.person_id == person_id)
        if admin_id is not None:
            query = query.filter(FaceEmbedding.admin_id == admin_id)
        else:
            query = query.filter(FaceEmbedding.admin_id.is_(None))
            
        db_record = query.first()
        
        if db_record:
            db_record.embedding = embedding_bytes
        else:
            db_record = FaceEmbedding(admin_id=admin_id, person_id=person_id, embedding=embedding_bytes)
            db.add(db_record)
            
        db.commit()
        
        # Update cache
        self._cache[(admin_id, person_id)] = embedding.astype(np.float32)
        return True

    def delete_face(self, db: Session, person_id: str, admin_id: Optional[str] = None) -> bool:
        """Delete a face embedding from database and cache matching admin_id + person_id"""
        query = db.query(FaceEmbedding).filter(FaceEmbedding.person_id == person_id)
        if admin_id is not None:
            query = query.filter(FaceEmbedding.admin_id == admin_id)
        else:
            query = query.filter(FaceEmbedding.admin_id.is_(None))
            
        db_record = query.first()
        if db_record:
            db.delete(db_record)
            db.commit()
            
            # Remove from cache
            cache_key = (admin_id, person_id)
            if cache_key in self._cache:
                del self._cache[cache_key]
            return True
        return False

    def get_total_faces(self, db: Session, admin_id: Optional[str] = None) -> int:
        """Get total number of registered faces, optionally filtered by admin_id"""
        if self._cache_loaded:
            if admin_id is not None:
                return sum(1 for (aid, _) in self._cache.keys() if aid == admin_id)
            return len(self._cache)
            
        if admin_id is not None:
            return db.query(FaceEmbedding).filter(FaceEmbedding.admin_id == admin_id).count()
        return db.query(FaceEmbedding).count()

    def find_best_match(
        self, 
        db: Session, 
        query_embedding: np.ndarray, 
        admin_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str], float]:
        """
        Compare query_embedding against registered faces using cosine similarity.
        If admin_id is provided, searches only faces registered under that admin_id.
        If admin_id is not provided, maintains backward compatibility searching legacy faces (admin_id is None).
        Returns: (is_match, person_id, admin_id, confidence_percentage)
        """
        # Ensure cache is loaded
        self.load_cache(db)
        
        if not self._cache:
            return False, None, admin_id, 0.0

        best_score = -1.0
        best_person_id = None
        best_admin_id = None
        
        # Convert query embedding to float32 for consistent comparison
        query_emb = query_embedding.astype(np.float32)
        norm_q = np.linalg.norm(query_emb)
        if norm_q == 0:
            return False, None, admin_id, 0.0
        
        for (cached_admin_id, person_id), stored_emb in self._cache.items():
            # Filter by admin_id
            if admin_id is not None:
                if cached_admin_id != admin_id:
                    continue
            else:
                if cached_admin_id is not None:
                    continue
            
            norm_s = np.linalg.norm(stored_emb)
            if norm_s == 0:
                continue
                
            sim = np.dot(query_emb, stored_emb) / (norm_q * norm_s)
            
            if sim > best_score:
                best_score = float(sim)
                best_person_id = person_id
                best_admin_id = cached_admin_id

        # Check threshold
        if best_score >= settings.MATCH_THRESHOLD:
            confidence = round(best_score * 100, 2)
            confidence = min(confidence, 100.0)
            return True, best_person_id, best_admin_id, confidence
            
        return False, None, admin_id, 0.0

embedding_service = EmbeddingService()
