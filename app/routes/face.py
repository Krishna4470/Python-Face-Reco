from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import RegisterFaceResponse, RecognizeFaceResponse, FaceCountResponse, BaseResponse
from app.security.api_key import get_api_key
from app.services.face_service import face_service
from app.services.embedding_service import embedding_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Face Recognition"],
    dependencies=[Depends(get_api_key)]
)

async def validate_file_size(file: UploadFile) -> bytes:
    # Read file content
    content = await file.read()
    # Check size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size allowed is {settings.MAX_UPLOAD_SIZE_MB}MB."
        )
    return content

@router.post("/register-face", response_model=RegisterFaceResponse)
async def register_face(
    person_id: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        if not image.content_type.startswith('image/'):
            return RegisterFaceResponse(success=False, error="Invalid file type. Please upload an image.")
            
        image_bytes = await validate_file_size(image)
        
        # Detect face and get embedding
        try:
            embedding = face_service.get_face_embedding(image_bytes)
        except ValueError as e:
            return RegisterFaceResponse(success=False, error=str(e))
            
        # Save to database
        embedding_service.register_face(db, person_id, embedding)
        
        return RegisterFaceResponse(
            success=True, 
            person_id=person_id, 
            message="Face registered successfully"
        )
    except Exception as e:
        logger.error(f"Error registering face: {str(e)}")
        return RegisterFaceResponse(success=False, error="Internal server error")

@router.post("/recognize-face", response_model=RecognizeFaceResponse)
async def recognize_face(
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        if not image.content_type.startswith('image/'):
            return RecognizeFaceResponse(success=False, matched=False, confidence=0, error="Invalid file type. Please upload an image.")
            
        image_bytes = await validate_file_size(image)
        
        # Detect face and get embedding
        try:
            query_embedding = face_service.get_face_embedding(image_bytes)
        except ValueError as e:
            return RecognizeFaceResponse(success=False, matched=False, confidence=0, error=str(e))
            
        # Find best match
        is_match, person_id, confidence = embedding_service.find_best_match(db, query_embedding)
        
        if is_match:
            return RecognizeFaceResponse(
                success=True,
                matched=True,
                person_id=person_id,
                confidence=confidence
            )
        else:
            return RecognizeFaceResponse(
                success=True,
                matched=False,
                person_id=None,
                confidence=0
            )
    except Exception as e:
        logger.error(f"Error recognizing face: {str(e)}")
        return RecognizeFaceResponse(success=False, matched=False, confidence=0, error="Internal server error")

@router.delete("/delete-face/{person_id}", response_model=BaseResponse)
async def delete_face(
    person_id: str,
    db: Session = Depends(get_db)
):
    try:
        deleted = embedding_service.delete_face(db, person_id)
        if deleted:
            return BaseResponse(success=True, message=f"Face for person_id {person_id} deleted successfully")
        else:
            return BaseResponse(success=False, error=f"Face for person_id {person_id} not found")
    except Exception as e:
        logger.error(f"Error deleting face: {str(e)}")
        return BaseResponse(success=False, error="Internal server error")

@router.get("/faces/count", response_model=FaceCountResponse)
async def get_face_count(db: Session = Depends(get_db)):
    try:
        count = embedding_service.get_total_faces(db)
        return FaceCountResponse(success=True, total_registered_faces=count)
    except Exception as e:
        logger.error(f"Error getting face count: {str(e)}")
        return FaceCountResponse(success=False, error="Internal server error")
