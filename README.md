# Face Recognition API with Liveness Detection

A production-ready Python API built with FastAPI, InsightFace, MediaPipe, and SQLite, designed to be deployed on Railway. This API works as a dedicated microservice that connects with an existing PHP + MySQL Attendance Management System.

## Features

- **Face Recognition**: Fast and lightweight face detection and recognition using InsightFace (CPU inference).
- **Liveness Detection (Blink Verification)**: MediaPipe-based eye blink detection using Eye Aspect Ratio (EAR) across a sequence of camera frames. 
- **Face Consistency Check**: Verifies that the blinking person matches the face submitted for recognition.
- **Storage**: Face embeddings stored safely in a local SQLite database using binary blobs.
- **Security**: Secure communication using `X-API-Key`. Basic rate-limiting included.
- **Caching**: In-memory caching of embeddings for ultra-fast recognition on low-resource environments.

## Blink Liveness Architecture

To prevent spoofing with static photos, the API requires a sequence of images (frames) captured while the user blinks.
The flow works as follows:
1. The frontend captures multiple frames while prompting the user to blink.
2. The frames are sent to `/api/verify-and-recognize`.
3. The API calculates the Eye Aspect Ratio (EAR) for both eyes in every frame.
4. It looks for a sequence where eyes transition from `OPEN` -> `CLOSED` -> `OPEN`.
5. If a blink is detected, it checks if the face in the liveness frames matches the recognition image.
6. Finally, it matches the face against the registered SQLite database.

## Requirements

- Python 3.11+

## Local Installation

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate # macOS/Linux
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to set your desired `API_SECRET_KEY` and liveness thresholds.*

4. **Run the FastAPI application locally**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing API Endpoints

Once the server is running locally, access the interactive API documentation at:
http://127.0.0.1:8000/docs

### Main Endpoints:
- `POST /api/register-face`: Register a new face with `person_id`.
- `POST /api/verify-liveness`: Test blink detection only (submit multiple frames).
- `POST /api/verify-and-recognize`: Production endpoint. Submit `frames` (for blink) and `recognition_image` (for matching).
- `POST /api/recognize-face`: Legacy recognition only (can be disabled via `REQUIRE_LIVENESS=true`).

## Deployment to Railway

1. Push your code to a GitHub repository.
2. Go to [Railway](https://railway.app/) and create a "New Project" -> "Deploy from GitHub repo".
3. In your Railway project dashboard, go to the "Variables" tab and add your `.env` variables (e.g., `API_SECRET_KEY`).
4. **IMPORTANT**: Go to the "Volumes" section in Railway settings and add a volume mounted to `/app/data` to ensure the SQLite database is not lost on restart.
5. Railway will automatically build and deploy the app.

## Security Limitations

While blink-based liveness improves security significantly against static photos, it is a basic anti-spoofing measure. It may not protect against advanced attacks (like deepfakes or high-res video playbacks). For higher security in the future, challenge randomization (e.g., turn left/right) can be added.
