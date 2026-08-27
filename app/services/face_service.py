import cv2
import numpy as np
from insightface.app import FaceAnalysis
import logging

logger = logging.getLogger(__name__)

class FaceService:
    def __init__(self):
        self.app = None

    def initialize_model(self):
        """Initialize the InsightFace model once on startup"""
        if self.app is None:
            logger.info("Initializing InsightFace model (CPU)...")
            # We use 'buffalo_s' for a lightweight model if possible, 
            # otherwise it defaults to buffalo_l
            self.app = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("InsightFace model initialized successfully.")

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        """Decode image bytes into an OpenCV image"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image")
            return img
        except Exception as e:
            logger.error(f"Image decoding error: {str(e)}")
            raise ValueError("Invalid or corrupted image format")

    def get_face_embedding(self, image_bytes: bytes) -> np.ndarray:
        """
        Detect exactly one face and return its normalized embedding.
        Raises ValueError if 0 or >1 faces are detected, or if image is invalid.
        """
        if self.app is None:
            raise RuntimeError("Face recognition model is not initialized")
            
        img = self.decode_image(image_bytes)
        
        faces = self.app.get(img)
        
        if len(faces) == 0:
            raise ValueError("No face detected in the uploaded image")
        if len(faces) > 1:
            raise ValueError("Multiple faces detected. Please use an image containing only one face.")
            
        face = faces[0]
        embedding = face.normed_embedding
        return embedding
        
    def decode_image(self, image_bytes: bytes) -> np.ndarray:
        return self._decode_image(image_bytes)

face_service = FaceService()
