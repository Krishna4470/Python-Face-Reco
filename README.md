# Face Recognition API

A production-ready Python Face Recognition API built with FastAPI, InsightFace, and SQLite, designed to be deployed on Railway. This API works as a dedicated microservice that connects with an existing PHP + MySQL Attendance Management System.

## Features

- Fast and lightweight face detection and recognition using InsightFace (CPU inference).
- Storage of face embeddings in a local SQLite database.
- Secure communication using an API Key.
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

## Testing API Endpoints

Once the server is running locally, you can access the automatically generated interactive API documentation (Swagger UI) at:
http://127.0.0.1:8000/docs

From there, you can test all the endpoints. Note that most endpoints require the `X-API-Key` header, which you can provide using the "Authorize" button in the Swagger UI.

## Deployment to Railway

1. **Upload the project to GitHub**:
   - Create a new repository on GitHub.
   - Commit all your files (ensure `.env` is NOT committed; it is ignored by `.gitignore`).
   - Push to your GitHub repository.

2. **Deploy to Railway**:
   - Go to [Railway](https://railway.app/).
   - Click "New Project" and choose "Deploy from GitHub repo".
   - Select your repository.
   - Railway will automatically detect the Python environment and use the `Procfile` to run the app.

3. **Configure Railway Environment Variables**:
   - In your Railway project dashboard, go to the "Variables" tab.
   - Add the variables from your `.env` file, especially:
     - `API_SECRET_KEY`
     - `MATCH_THRESHOLD`
     - `MAX_UPLOAD_SIZE_MB`
   - You can leave `DATABASE_URL` as default if you want to use ephemeral storage, or attach a persistent volume to the `/app/data` directory and update the `DATABASE_URL` accordingly.

4. **Get the Railway Public API URL**:
   - Railway will generate a public domain for your service (e.g., `https://your-app-production.up.railway.app`).
   - Use this URL in your PHP application to make API requests.

## PHP Integration

The PHP attendance website should call this Python API using HTTP POST/DELETE requests. Ensure to include the API Key in the headers.

Example PHP cURL request to register a face:

```php
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, "https://<your-railway-url>/api/register-face");
curl_setopt($ch, CURLOPT_POST, 1);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    "X-API-Key: " . $YOUR_API_SECRET_KEY
));

$cfile = new CURLFile('/path/to/image.jpg', 'image/jpeg', 'image');
$data = array(
    'person_id' => '25127335500020',
    'image' => $cfile
);
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
curl_close($ch);
```
