from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import RegisterFaceResponse, RecognizeFaceResponse, FaceCountResponse, BaseResponse, VerifyAndRecognizeResponse
from app.security.api_key import get_api_key
from app.security.rate_limit import check_rate_limit
from app.services.face_service import face_service
from app.services.embedding_service import embedding_service
from app.services.liveness_service import liveness_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Face Recognition"],
    dependencies=[Depends(get_api_key), Depends(check_rate_limit)]
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

@router.post("/verify-and-recognize", response_model=VerifyAndRecognizeResponse)
async def verify_and_recognize(
    frames: List[UploadFile] = File(...),
    recognition_image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Perform liveness verification on a sequence of frames, and if successful,
    recognize the face in the recognition_image. Also checks consistency between liveness face and recognition face.
    """
    if not settings.REQUIRE_LIVENESS:
        # If disabled, fallback to normal recognition without liveness checks
        logger.info("Liveness bypassed by configuration.")
        # We can just call recognize_face logic, but we need to return VerifyAndRecognizeResponse
        # For simplicity, if bypassed, just process the recognition image
        rec_res = await recognize_face(image=recognition_image, db=db)
        return VerifyAndRecognizeResponse(
            success=rec_res.success,
            liveness_passed=True,
            matched=rec_res.matched,
            person_id=rec_res.person_id,
            confidence=rec_res.confidence,
            error=rec_res.error
        )

    try:
        from app.routes.liveness import validate_and_read_frames
        
        # 1. Validate frames
        image_bytes_list = await validate_and_read_frames(frames)
        
        # 2. Check Liveness (Blink)
        blink_detected, blinks_count, best_liveness_img = liveness_service.process_frames_for_blink(image_bytes_list)
        
        if not blink_detected:
            logger.warning("Verify & Recognize: Liveness failed (No blink).")
            return VerifyAndRecognizeResponse(
                success=False,
                liveness_passed=False,
                matched=False,
                message="Liveness verification failed. Please blink and try again."
            )
            
        # 3. Liveness passed. Now get embedding for the liveness face for consistency check
        liveness_embedding = face_service.get_face_embedding_from_image(best_liveness_img)
        
        # 4. Process Recognition Image
        if not recognition_image.content_type.startswith('image/'):
            return VerifyAndRecognizeResponse(success=False, liveness_passed=True, matched=False, error="Invalid recognition image file type.")
            
        rec_image_bytes = await validate_file_size(recognition_image)
        rec_embedding = face_service.get_face_embedding(rec_image_bytes)
        
        # 5. Face Consistency Check
        consistency_score = embedding_service.compare_embeddings(liveness_embedding, rec_embedding)
        if consistency_score < settings.LIVENESS_FACE_MATCH_THRESHOLD:
            logger.warning(f"Verify & Recognize: Face consistency failed. Score: {consistency_score}")
            return VerifyAndRecognizeResponse(
                success=False,
                liveness_passed=False,
                matched=False,
                message="Face consistency verification failed. The blinking person does not match the recognition image."
            )
            
        # 6. Face Matching
        is_match, person_id, confidence = embedding_service.find_best_match(db, rec_embedding)
        
        if is_match:
            logger.info(f"Verify & Recognize: Success for {person_id}")
            return VerifyAndRecognizeResponse(
                success=True,
                liveness_passed=True,
                matched=True,
                person_id=person_id,
                confidence=confidence,
                message="Liveness verified and face recognized successfully."
            )
        else:
            logger.info("Verify & Recognize: Liveness passed, but face not recognized.")
            return VerifyAndRecognizeResponse(
                success=True,
                liveness_passed=True,
                matched=False,
                person_id=None,
                confidence=0,
                message="Liveness verified, but face was not recognized."
            )

    except HTTPException as e:
        raise e
    except ValueError as e:
        logger.error(f"Verify & Recognize error: {str(e)}")
        return VerifyAndRecognizeResponse(success=False, liveness_passed=False, error=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Verify & Recognize internal error: {traceback.format_exc()}")
        return VerifyAndRecognizeResponse(success=False, liveness_passed=False, error=f"Internal server error: {str(e)}")
