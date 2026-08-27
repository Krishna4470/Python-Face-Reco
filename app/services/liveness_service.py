import cv2
import numpy as np
import mediapipe as mp
import logging
from typing import List, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

# Eye landmarks based on MediaPipe FaceMesh
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

class LivenessService:
    def __init__(self):
        self.face_mesh = None

    def initialize_model(self):
        """Initialize MediaPipe FaceMesh once on startup"""
        if self.face_mesh is None:
            logger.info("Initializing MediaPipe FaceMesh for liveness detection...")
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe FaceMesh initialized successfully.")

    def _calculate_ear(self, landmarks, eye_indices: List[int]) -> float:
        """Calculate Eye Aspect Ratio (EAR) given face landmarks and eye indices."""
        # eye_indices: [p1, p2, p3, p4, p5, p6]
        # p1 = left/right corner, p4 = right/left corner
        # p2, p3 = top eyelid
        # p5, p6 = bottom eyelid
        
        # We need numpy arrays of coordinates
        pts = np.array([[landmarks.landmark[i].x, landmarks.landmark[i].y] for i in eye_indices])
        
        # Vertical eye distances
        dist1 = np.linalg.norm(pts[1] - pts[5])
        dist2 = np.linalg.norm(pts[2] - pts[4])
        
        # Horizontal eye distance
        dist3 = np.linalg.norm(pts[0] - pts[3])
        
        ear = (dist1 + dist2) / (2.0 * dist3)
        return ear

    def process_frames_for_blink(self, image_bytes_list: List[bytes]) -> Tuple[bool, int, np.ndarray]:
        """
        Process a sequence of frames to detect a valid blink (OPEN -> CLOSED -> OPEN).
        Returns: (blink_detected, number_of_blinks, best_face_image_numpy)
        Raises ValueError if frames are invalid.
        """
        if self.face_mesh is None:
            raise RuntimeError("Liveness model is not initialized")
            
        if len(image_bytes_list) < settings.MIN_LIVENESS_FRAMES:
            raise ValueError(f"Insufficient frames. Minimum {settings.MIN_LIVENESS_FRAMES} frames required.")
            
        if len(image_bytes_list) > settings.MAX_LIVENESS_FRAMES:
            # Process only up to max frames to save memory/CPU
            image_bytes_list = image_bytes_list[:settings.MAX_LIVENESS_FRAMES]

        state = "OPEN"
        blinks = 0
        best_frame = None
        max_ear = -1.0 # Keep the frame where eyes are most wide open as the best frame

        for frame_bytes in image_bytes_list:
            # Decode image
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                continue
                
            # MediaPipe requires RGB
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Process with FaceMesh
            results = self.face_mesh.process(rgb_img)
            
            if not results.multi_face_landmarks:
                continue # No face found in this frame
                
            landmarks = results.multi_face_landmarks[0]
            
            left_ear = self._calculate_ear(landmarks, LEFT_EYE)
            right_ear = self._calculate_ear(landmarks, RIGHT_EYE)
            
            avg_ear = (left_ear + right_ear) / 2.0
            
            # Keep track of the best frame (eyes wide open) for face consistency check
            if avg_ear > max_ear:
                max_ear = avg_ear
                best_frame = img
            
            # Blink State Machine (OPEN -> CLOSED -> OPEN)
            if state == "OPEN":
                if avg_ear < settings.LIVENESS_EAR_CLOSED_THRESHOLD:
                    state = "CLOSED"
            elif state == "CLOSED":
                if avg_ear > settings.LIVENESS_EAR_OPEN_THRESHOLD:
                    state = "OPEN"
                    blinks += 1
                    
        # Clean up resources for this run
        # Note: FaceMesh maintains temporal state if static_image_mode=False
        # It's better to reset it between completely separate requests.
        self.face_mesh.process(np.zeros((10, 10, 3), dtype=np.uint8)) 

        if best_frame is None:
            raise ValueError("No face detected in any of the provided frames.")

        blink_detected = blinks >= settings.REQUIRED_BLINKS
        
        return blink_detected, blinks, best_frame

liveness_service = LivenessService()
