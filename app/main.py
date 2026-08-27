import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import health, face
from app.services.face_service import face_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up Face Recognition API...")
    try:
        face_service.initialize_model()
    except Exception as e:
        logger.error(f"Failed to initialize Face Recognition model: {e}")
        # Depending on deployment, you might want to raise to crash the app,
        # or keep it alive so /health returns something (though model won't work).
        # We'll log the error and let it proceed, routes will catch the Uninitialized error.
    
    yield
    # Shutdown logic
    logger.info("Shutting down Face Recognition API...")

app = FastAPI(
    title="Face Recognition API",
    description="Python Face Recognition API for PHP Attendance Management System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(face.router)
