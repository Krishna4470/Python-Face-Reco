from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from typing import Optional
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

def normalize_admin_id(admin_id: Optional[str]) -> Optional[str]:
    """Normalize admin_id: empty strings, 'null', 'none' are treated as None"""
    if admin_id is None:
        return None
    cleaned = str(admin_id).strip()
    if cleaned == "" or cleaned.lower() in ("null", "none", "undefined"):
        return None
    return cleaned

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
    person_id: str = Form(..., description="Required identifier of the person"),
    image: UploadFile = File(..., description="Image file containing exactly one face"),
    admin_id: Optional[str] = Form(None, description="Optional admin ID to isolate person registration"),
    db: Session = Depends(get_db)
):
    try:
        person_id_clean = person_id.strip()
        if not person_id_clean:
            return RegisterFaceResponse(success=False, error="person_id is required")

        norm_admin_id = normalize_admin_id(admin_id)

        if not image.content_type.startswith('image/'):
            return RegisterFaceResponse(
                success=False, 
                admin_id=norm_admin_id,
                person_id=person_id_clean,
                error="Invalid file type. Please upload an image."
            )
            
        image_bytes = await validate_file_size(image)
        
        # Detect face and get embedding
        try:
            embedding = face_service.get_face_embedding(image_bytes)
        except ValueError as e:
            return RegisterFaceResponse(
                success=False, 
                admin_id=norm_admin_id,
                person_id=person_id_clean,
                error=str(e)
            )
            
        # Save to database and cache
        embedding_service.register_face(db, person_id_clean, embedding, norm_admin_id)
        
        return RegisterFaceResponse(
            success=True, 
            admin_id=norm_admin_id,
            person_id=person_id_clean, 
            message="Face registered successfully"
        )
    except Exception as e:
        logger.error(f"Error registering face: {str(e)}")
        return RegisterFaceResponse(
            success=False, 
            admin_id=normalize_admin_id(admin_id),
            person_id=person_id.strip() if person_id else None,
            error="Internal server error"
        )

@router.post("/recognize-face", response_model=RecognizeFaceResponse)
async def recognize_face(
    image: UploadFile = File(..., description="Image file containing the face to recognize"),
    admin_id: Optional[str] = Form(None, description="Optional admin ID to scope face search to this admin"),
    db: Session = Depends(get_db)
):
    norm_admin_id = normalize_admin_id(admin_id)
    try:
        if not image.content_type.startswith('image/'):
            return RecognizeFaceResponse(
                success=False, 
                admin_id=norm_admin_id,
                matched=False, 
                confidence=0.0, 
                error="Invalid file type. Please upload an image."
            )
            
        image_bytes = await validate_file_size(image)
        
        # Detect face and get embedding
        try:
            query_embedding = face_service.get_face_embedding(image_bytes)
        except ValueError as e:
            return RecognizeFaceResponse(
                success=False, 
                admin_id=norm_admin_id,
                matched=False, 
                confidence=0.0, 
                error=str(e)
            )
            
        # Find best match
        is_match, person_id, matched_admin_id, confidence = embedding_service.find_best_match(
            db, 
            query_embedding, 
            norm_admin_id
        )
        
        if is_match:
            return RecognizeFaceResponse(
                success=True,
                matched=True,
                admin_id=matched_admin_id,
                person_id=person_id,
                confidence=confidence
            )
        else:
            return RecognizeFaceResponse(
                success=True,
                matched=False,
                admin_id=norm_admin_id,
                person_id=None,
                confidence=0.0
            )
    except Exception as e:
        logger.error(f"Error recognizing face: {str(e)}")
        return RecognizeFaceResponse(
            success=False, 
            admin_id=norm_admin_id,
            matched=False, 
            confidence=0.0, 
            error="Internal server error"
        )

@router.delete("/delete-face/{person_id}", response_model=BaseResponse)
async def delete_face(
    person_id: str,
    admin_id: Optional[str] = Query(None, description="Optional admin ID to scope face deletion"),
    db: Session = Depends(get_db)
):
    norm_admin_id = normalize_admin_id(admin_id)
    try:
        deleted = embedding_service.delete_face(db, person_id.strip(), norm_admin_id)
        if deleted:
            scope_desc = f" under admin_id {norm_admin_id}" if norm_admin_id else ""
            return BaseResponse(
                success=True, 
                admin_id=norm_admin_id,
                message=f"Face for person_id {person_id}{scope_desc} deleted successfully"
            )
        else:
            scope_desc = f" under admin_id {norm_admin_id}" if norm_admin_id else ""
            return BaseResponse(
                success=False, 
                admin_id=norm_admin_id,
                error=f"Face for person_id {person_id}{scope_desc} not found"
            )
    except Exception as e:
        logger.error(f"Error deleting face: {str(e)}")
        return BaseResponse(
            success=False, 
            admin_id=norm_admin_id,
            error="Internal server error"
        )

@router.get("/faces/count", response_model=FaceCountResponse)
async def get_face_count(
    admin_id: Optional[str] = Query(None, description="Optional admin ID to count faces for specific admin"),
    db: Session = Depends(get_db)
):
    norm_admin_id = normalize_admin_id(admin_id)
    try:
        count = embedding_service.get_total_faces(db, norm_admin_id)
        return FaceCountResponse(
            success=True, 
            admin_id=norm_admin_id,
            total_registered_faces=count
        )
    except Exception as e:
        logger.error(f"Error getting face count: {str(e)}")
        return FaceCountResponse(
            success=False, 
            admin_id=norm_admin_id,
            error="Internal server error"
        )
