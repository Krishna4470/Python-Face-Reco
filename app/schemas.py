from pydantic import BaseModel
from typing import Optional

class BaseResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    message: Optional[str] = None

class RegisterFaceResponse(BaseResponse):
    person_id: Optional[str] = None

class RecognizeFaceResponse(BaseResponse):
    matched: Optional[bool] = None
    person_id: Optional[str] = None
    confidence: Optional[float] = None

class FaceCountResponse(BaseResponse):
    total_registered_faces: Optional[int] = None
