from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from typing import List
import logging
from app.schemas import LivenessResponse
from app.security.api_key import get_api_key
from app.security.rate_limit import check_rate_limit
from app.services.liveness_service import liveness_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Liveness"],
    dependencies=[Depends(get_api_key), Depends(check_rate_limit)]
)

async def validate_and_read_frames(frames: List[UploadFile]) -> List[bytes]:
    """Validate and read a list of uploaded frame images."""
    if len(frames) < settings.MIN_LIVENESS_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {settings.MIN_LIVENESS_FRAMES} frames are required for liveness detection."
        )
        
    image_bytes_list = []
    # Only process up to MAX_LIVENESS_FRAMES to save memory
    for file in frames[:settings.MAX_LIVENESS_FRAMES]:
        if not file.content_type.startswith('image/'):
            continue
            
        content = await file.read()
        
        # Check size per frame (e.g. max 5MB per frame)
        if len(content) > (5 * 1024 * 1024):
            continue
            
        image_bytes_list.append(content)
        
    if len(image_bytes_list) < settings.MIN_LIVENESS_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough valid image frames provided."
        )
        
    return image_bytes_list

@router.post("/verify-liveness", response_model=LivenessResponse)
async def verify_liveness(frames: List[UploadFile] = File(...)):
    """
    Verify liveness by detecting an eye blink across a sequence of frames.
    """
    if not settings.REQUIRE_LIVENESS:
        return LivenessResponse(
            success=True, 
            liveness_passed=True, 
            message="Liveness check is disabled in configuration."
        )
        
    try:
        image_bytes_list = await validate_and_read_frames(frames)
        
        blink_detected, blinks_count, _ = liveness_service.process_frames_for_blink(image_bytes_list)
        
        if blink_detected:
            logger.info("Liveness verification passed (Blink detected).")
            return LivenessResponse(
                success=True,
                liveness_passed=True,
                blink_detected=True,
                blinks_detected=blinks_count,
                message="Liveness verification successful"
            )
        else:
            logger.warning("Liveness verification failed (No blink detected).")
            return LivenessResponse(
                success=True,
                liveness_passed=False,
                blink_detected=False,
                blinks_detected=blinks_count,
                message="Blink not detected. Please try again."
            )
            
    except ValueError as e:
        logger.error(f"Liveness error: {str(e)}")
        return LivenessResponse(success=False, liveness_passed=False, error=str(e))
    except Exception as e:
        logger.error(f"Internal liveness error: {str(e)}")
        return LivenessResponse(success=False, liveness_passed=False, error="Internal server error")
