Create a complete, production-ready Python Face Recognition API that will be deployed separately on Railway.

The Python application must work as a dedicated face recognition microservice and connect with an existing PHP + MySQL Attendance Management System through HTTP REST APIs.

## Project Purpose

The existing PHP attendance website will handle:

* Admin authentication
* Student/employee management
* Attendance sessions
* Attendance records
* Reports
* Main MySQL database
* Website UI

This Python application must handle only:

* Face detection
* Face validation
* Face embedding generation
* Face embedding storage
* Face recognition
* Face matching
* Returning person IDs and confidence scores to the PHP application

The Python application must NOT create a separate dashboard or frontend.

It should work purely as a REST API.

## Technology Stack

Use:

* Python 3.11
* FastAPI
* Uvicorn
* InsightFace
* ONNX Runtime CPU
* NumPy
* OpenCV
* SQLAlchemy
* SQLite for local face embedding storage
* Pydantic
* Python multipart file uploads

Do not use Face++.

The face recognition model should run directly inside the Python application.

Use a lightweight and Railway-compatible InsightFace configuration suitable for CPU inference and limited RAM.

## Important Architecture

The architecture should be:

PHP Attendance Website
↓ HTTPS REST API
Python Face Recognition API
↓
InsightFace
↓
Face Detection + Embedding + Recognition

The PHP application remains the main application.

The Python application only returns:

* person_id
* matched status
* confidence score
* recognition result

The Python application must not manage attendance records.

The PHP application will mark attendance after receiving a successful recognition result.

## Person Registration Flow

The existing PHP website will send:

* person_id
* face image

to the Python API.

The flow should be:

PHP Website
↓
POST /api/register-face
↓
Python API receives person_id + image
↓
Validate image
↓
Detect face
↓
Validate exactly one face
↓
Generate face embedding
↓
Normalize embedding
↓
Save person_id + embedding
↓
Return success response

The API must reject:

* No face detected
* Multiple faces detected
* Invalid image
* Corrupted image
* Unsupported file type

Example successful response:

```json
{
  "success": true,
  "person_id": "25127335500020",
  "message": "Face registered successfully"
}
```

Example error:

```json
{
  "success": false,
  "error": "Multiple faces detected. Please use an image containing only one face."
}
```

## Face Recognition Flow

The existing PHP attendance website will capture a face image from the browser camera and send it to the Python API.

The flow:

Camera
↓
PHP Website
↓
POST /api/recognize-face
↓
Python API
↓
Detect Face
↓
Generate Embedding
↓
Compare With Registered Embeddings
↓
Find Best Match
↓
Return person_id + confidence

Example successful response:

```json
{
  "success": true,
  "matched": true,
  "person_id": "25127335500020",
  "confidence": 92.45
}
```

Example unmatched response:

```json
{
  "success": true,
  "matched": false,
  "person_id": null,
  "confidence": 0
}
```

The PHP application will then use the returned `person_id` to fetch the student's details from its MySQL database and mark attendance.

## Face Matching

Use cosine similarity for comparing normalized face embeddings.

Implement a configurable recognition threshold.

Example:

```text
MATCH_THRESHOLD=0.55
```

The system should:

1. Generate an embedding from the scanned face.
2. Compare it with all registered embeddings.
3. Find the highest similarity score.
4. Return a match only if the score is above the configured threshold.
5. Otherwise return `matched: false`.

The threshold must be configurable using environment variables.

Do not hardcode it in the source code.

## Required API Endpoints

### 1. Health Check

```text
GET /health
```

Response:

```json
{
  "status": "healthy",
  "service": "face-recognition-api"
}
```

### 2. Register Face

```text
POST /api/register-face
```

Accept multipart/form-data:

```text
person_id
image
```

Requirements:

* `person_id` must be required.
* If the person already has an embedding, replace/update the old embedding.
* Detect exactly one face.
* Generate and save the face embedding.

### 3. Recognize Face

```text
POST /api/recognize-face
```

Accept:

```text
image
```

Requirements:

* Detect exactly one face.
* Generate embedding.
* Compare against registered embeddings.
* Return the best match.

### 4. Delete Face

```text
DELETE /api/delete-face/{person_id}
```

Delete the stored face embedding when a person is deleted from the PHP system.

### 5. List Registered Faces

```text
GET /api/faces/count
```

Return:

```json
{
  "success": true,
  "total_registered_faces": 60
}
```

Do not return actual face embeddings through public API responses.

## API Security

Secure all sensitive API endpoints using an API key.

Use an environment variable:

```text
API_SECRET_KEY
```

Require the PHP application to send:

```text
X-API-Key: YOUR_SECRET_KEY
```

Create middleware or a reusable security dependency to validate the API key.

The `/health` endpoint can remain public.

## Environment Variables

Use a `.env.example` file containing:

```text
API_SECRET_KEY=change_this_secret
MATCH_THRESHOLD=0.55
MAX_UPLOAD_SIZE_MB=10
DATABASE_URL=sqlite:///./data/faces.db
```

Never hardcode secrets in the source code.

## Database

Use SQLite with SQLAlchemy.

Create a table for face embeddings:

```text
face_embeddings
--------------------------
id
person_id
embedding
created_at
updated_at
```

Requirements:

* `person_id` must be unique.
* Store embeddings efficiently.
* Do not expose embeddings through API responses.
* Automatically create required tables on startup.

Use Railway persistent storage/volume for the SQLite database if persistent local storage is needed.

Make the database path configurable using the `DATABASE_URL` environment variable.

## InsightFace Implementation

Use InsightFace with ONNX Runtime CPU.

Requirements:

* Load the model only once during application startup.
* Do not reload the model on every request.
* Use CPU execution provider.
* Keep memory usage as low as possible.
* Avoid unnecessary large dependencies.
* Use efficient image decoding.
* Limit maximum uploaded file size.

Handle startup errors properly.

## Railway Deployment Requirements

The project must be ready for Railway deployment.

Include:

### requirements.txt

Include all required Python packages.

### Procfile or Railway-compatible startup command

The application must run with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Make sure the application automatically uses Railway's `$PORT` environment variable.

### railway.json or other Railway configuration if useful

Configure deployment correctly.

### Dockerfile

Only include a Dockerfile if required for reliable InsightFace/ONNX deployment.

If a Dockerfile is used:

* Use a lightweight Python base image.
* Install only required system dependencies.
* Avoid unnecessary packages.
* Optimize image size where practical.

The final project must deploy directly to Railway from a GitHub repository.

## CORS

Configure CORS securely.

Allow the PHP website domain through environment variables.

Example:

```text
ALLOWED_ORIGINS=https://your-website.infinityfreeapp.com
```

Do not use unrestricted CORS in production unless required for testing.

## Performance Requirements

The Railway environment may have limited CPU and RAM.

Optimize the application for approximately:

* 50 to 60 registered users
* Sequential face recognition
* Small attendance system
* CPU-only inference

Important:

The number of registered users should not cause the InsightFace model to reload.

Load all registered embeddings efficiently.

For recognition, avoid unnecessary database operations when possible.

Implement caching of embeddings in memory if safe, but make sure registration, updates, and deletion correctly refresh the cache.

## Error Handling

Return consistent JSON responses.

Handle:

* Invalid API key
* Missing person_id
* Missing image
* Invalid image
* Image too large
* No face detected
* Multiple faces detected
* Face recognition model error
* Database errors
* Internal server errors

Example error:

```json
{
  "success": false,
  "error": "No face detected in the uploaded image"
}
```

Do not expose internal stack traces in production responses.

## Project Structure

Use this clean structure:

```text
face-recognition-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── face.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── face_service.py
│   │   └── embedding_service.py
│   │
│   └── security/
│       ├── __init__.py
│       └── api_key.py
│
├── data/
│   └── .gitkeep
│
├── requirements.txt
├── .env.example
├── README.md
├── railway.json
├── Procfile
└── .gitignore
```

## Important Implementation Rules

* Generate complete working code.
* Do not generate placeholder functions.
* Do not use Face++ or any external face recognition API.
* Use InsightFace locally inside the Python application.
* Use FastAPI.
* Optimize for Railway free/low-resource environments.
* Load the AI model only once.
* Support 50–60 registered persons efficiently.
* Return only `person_id`, match status, and confidence to the PHP website.
* Do not manage attendance in the Python application.
* Keep face recognition logic separate from the PHP attendance website.
* Make API communication secure using `X-API-Key`.
* Include proper logging.
* Include a complete README.

## README Requirements

Explain step by step:

1. How to install locally.
2. How to create and activate a virtual environment.
3. How to install dependencies.
4. How to configure environment variables.
5. How to run the FastAPI application locally.
6. How to test every API endpoint using FastAPI Swagger documentation.
7. How to upload the project to GitHub.
8. How to deploy the project to Railway.
9. How to configure Railway environment variables.
10. How to get the Railway public API URL.
11. How the PHP attendance website should call the Python API.

The project should be generated completely, starting with the folder structure and then all source files.
