from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from .database import Base

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(100), nullable=True, index=True)
    person_id = Column(String(100), index=True, nullable=False)
    embedding = Column(LargeBinary, nullable=False) # Store numpy array as bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('admin_id', 'person_id', name='uq_admin_person'),
        Index(
            'ix_face_embeddings_null_admin_person',
            'person_id',
            unique=True,
            sqlite_where=Column('admin_id').is_(None)
        ),
    )
