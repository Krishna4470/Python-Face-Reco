from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations():
    """Safely migrate database to support optional admin_id without data loss"""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "face_embeddings" not in tables:
            # Table will be created by Base.metadata.create_all
            return

        columns = [col["name"] for col in inspector.get_columns("face_embeddings")]
        if "admin_id" not in columns:
            logger.info("Migrating face_embeddings table to add optional admin_id support...")
            with engine.begin() as conn:
                if settings.DATABASE_URL.startswith("sqlite"):
                    # SQLite table migration to safely update constraints while keeping all existing records
                    conn.execute(text("""
                        CREATE TABLE face_embeddings_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            admin_id VARCHAR(100),
                            person_id VARCHAR(100) NOT NULL,
                            embedding BLOB NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT uq_admin_person UNIQUE (admin_id, person_id)
                        );
                    """))
                    conn.execute(text("""
                        INSERT INTO face_embeddings_new (id, admin_id, person_id, embedding, created_at, updated_at)
                        SELECT id, NULL, person_id, embedding, created_at, updated_at FROM face_embeddings;
                    """))
                    conn.execute(text("DROP TABLE face_embeddings;"))
                    conn.execute(text("ALTER TABLE face_embeddings_new RENAME TO face_embeddings;"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_face_embeddings_admin_id ON face_embeddings(admin_id);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_face_embeddings_person_id ON face_embeddings(person_id);"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_face_embeddings_null_admin_person ON face_embeddings(person_id) WHERE admin_id IS NULL;"))
                else:
                    # Non-sqlite alter
                    conn.execute(text("ALTER TABLE face_embeddings ADD COLUMN admin_id VARCHAR(100);"))
            logger.info("Database migration completed successfully.")
        else:
            # Ensure partial unique index exists for NULL admin_id in SQLite
            if settings.DATABASE_URL.startswith("sqlite"):
                with engine.begin() as conn:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_face_embeddings_null_admin_person ON face_embeddings(person_id) WHERE admin_id IS NULL;"))
    except Exception as e:
        logger.error(f"Database migration error: {e}")
