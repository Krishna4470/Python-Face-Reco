# Face Recognition API

A production-ready Python Face Recognition API built with FastAPI, InsightFace, and SQLite, designed to be deployed on Railway. This API works as a dedicated microservice that connects with an existing PHP + MySQL Attendance Management System.

## Features

- Fast and lightweight face detection and recognition using InsightFace (CPU inference).
- Multi-tenant face management via optional `admin_id` isolation.
- Full backward compatibility for single-tenant / legacy usage without `admin_id`.
- Storage of face embeddings in a local SQLite database with automatic schema migrations.
- In-memory embedding cache for high-speed face recognition matching.
- Secure communication using an API Key (`X-API-Key`).
- Environment variable based configuration.

## Requirements

- Python 3.11+

## Local Installation

1. **Clone the repository** (if applicable):
   ```bash
   git clone <your-repo-url>
   cd face-recognition-api
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate on Windows
   venv\Scripts\activate

   # Activate on macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Copy the example environment file and edit it with your settings.
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to set your desired `API_SECRET_KEY` and other configurations.*

5. **Run the FastAPI application locally**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Multi-Tenant Support (`admin_id`)

The `admin_id` parameter is **OPTIONAL** across all API endpoints:

- **When `admin_id` is provided**: The API scopes and isolates face data using the combination of `(admin_id, person_id)`. Different admins can independently register and recognize the same `person_id` (e.g. `admin_id=10, person_id=12345` and `admin_id=20, person_id=12345` are distinct records).
- **When `admin_id` is omitted, empty, or null**: The API maintains 100% backward compatibility using only `person_id` (unscoped/legacy records).

### Uniqueness Rules
| `admin_id` | `person_id` | Behavior |
|---|---|---|
| `10` | `12345` | Valid (Scoped to Admin 10) |
| `20` | `12345` | Valid (Scoped to Admin 20) |
| `10` | `12345` | Re-registration updates existing record for Admin 10 |
| `NULL` / omitted | `99999` | Valid (Legacy unscoped record) |

---

## API Endpoints

All endpoints except `/health` require the `X-API-Key` header.

### 1. Register Face
- **Endpoint**: `POST /api/register-face`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `person_id` (string, required): Identifier for the person.
  - `image` (file, required): Image file containing exactly one clear human face.
  - `admin_id` (string, **optional**): Admin or organization identifier.

**Response Example (with `admin_id`):**
```json
{
  "success": true,
  "admin_id": "10",
  "person_id": "12345",
  "message": "Face registered successfully"
}
```

**Response Example (without `admin_id`):**
```json
{
  "success": true,
  "admin_id": null,
  "person_id": "12345",
  "message": "Face registered successfully"
}
```

---

### 2. Recognize Face
- **Endpoint**: `POST /api/recognize-face`
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image` (file, required): Image file containing a human face to match.
  - `admin_id` (string, **optional**): When provided, searches only within faces registered under this `admin_id`.

**Response Example (Match Found):**
```json
{
  "success": true,
  "matched": true,
  "admin_id": "10",
  "person_id": "12345",
  "confidence": 88.54
}
```

**Response Example (No Match):**
```json
{
  "success": true,
  "matched": false,
  "admin_id": "10",
  "person_id": null,
  "confidence": 0.0
}
```

---

### 3. Delete Face
- **Endpoint**: `DELETE /api/delete-face/{person_id}?admin_id=10`
- **Parameters**:
  - `person_id` (path, required): Person ID to delete.
  - `admin_id` (query, **optional**): Admin ID scoping the face record.

**Response Example:**
```json
{
  "success": true,
  "admin_id": "10",
  "message": "Face for person_id 12345 under admin_id 10 deleted successfully"
}
```

---

### 4. Face Count
- **Endpoint**: `GET /api/faces/count?admin_id=10`
- **Parameters**:
  - `admin_id` (query, **optional**): Count faces registered under a specific admin (or all faces if omitted).

**Response Example:**
```json
{
  "success": true,
  "admin_id": "10",
  "total_registered_faces": 42
}
```

---

### 5. Health Check
- **Endpoint**: `GET /health` (No authentication required)

---

## PHP Integration Examples

### Register Face (with `admin_id`)

```php
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, "https://<your-railway-url>/api/register-face");
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    "X-API-Key: " . $YOUR_API_SECRET_KEY
));

$cfile = new CURLFile('/path/to/image.jpg', 'image/jpeg', 'image');
$data = array(
    'admin_id'  => '10', // Optional
    'person_id' => '12345',
    'image'     => $cfile
);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);
```

### Recognize Face (with `admin_id`)

```php
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, "https://<your-railway-url>/api/recognize-face");
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    "X-API-Key: " . $YOUR_API_SECRET_KEY
));

$cfile = new CURLFile('/path/to/scan.jpg', 'image/jpeg', 'image');
$data = array(
    'admin_id' => '10', // Optional: searches only Admin 10's faces
    'image'    => $cfile
);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);
```

### Delete Face (with `admin_id`)

```php
$person_id = '12345';
$admin_id = '10'; // Optional

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, "https://<your-railway-url>/api/delete-face/{$person_id}?admin_id={$admin_id}");
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "DELETE");
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    "X-API-Key: " . $YOUR_API_SECRET_KEY
));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);
```

---

## Deployment to Railway

1. **Upload the project to GitHub**:
   - Commit all files (ensure `.env` is NOT committed).
   - Push to your GitHub repository.

2. **Deploy to Railway**:
   - Go to [Railway](https://railway.app/).
   - Click "New Project" and choose "Deploy from GitHub repo".
   - Railway automatically uses the `Procfile` and `railway.json` to deploy.

3. **Configure Railway Environment Variables**:
   - `API_SECRET_KEY`
   - `MATCH_THRESHOLD` (e.g. `0.55`)
   - `MAX_UPLOAD_SIZE_MB` (e.g. `10`)
   - `DATABASE_URL` (e.g. `sqlite:///./data/faces.db`)
