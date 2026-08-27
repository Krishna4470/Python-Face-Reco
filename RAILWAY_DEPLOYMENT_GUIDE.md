# Railway Deployment Walkthrough (Step-by-Step)

Yeh guide aapko batayegi ki apne Python Face Recognition API ko Railway (railway.app) par kaise host karna hai.

## Step 1: GitHub par Code Push Karein

Railway directly GitHub se code pull karke deploy karta hai. Sabse pehle apna code GitHub par daalein.

1. Agar aapne abhi tak Git initialize nahi kiya hai, toh project folder (`f:\Python-Face-Reco`) mein terminal/command prompt kholiye aur run karein:
   ```bash
   git init
   ```
2. Saare files add karein:
   ```bash
   git add .
   ```
3. Commit karein:
   ```bash
   git commit -m "Initial commit - Face Reco API"
   ```
4. GitHub par ek naya blank repository banayein.
5. GitHub ke diye gaye commands run karke code push karein:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```
   *(Note: `.env` file push nahi honi chahiye kyunki woh `.gitignore` mein hai, jo ki security ke liye achha hai)*

## Step 2: Railway par Project Banayein

1. [Railway.app](https://railway.app/) par jayein aur login karein (apne GitHub account se login karna best rahega).
2. Dashboard mein **"New Project"** par click karein.
3. **"Deploy from GitHub repo"** select karein.
4. Agar pehli baar kar rahe hain toh Railway ko apne GitHub ka access dein.
5. Apni Face Recognition repository select karein aur **"Deploy Now"** par click karein.

## Step 3: Environment Variables Setup Karein

Jab deployment start hogi, woh shayad fail ho jaye ya theek se run na ho kyunki humne environment variables (jaise API Key) set nahi kiye hain.

1. Apne naye Railway project mein apna app (service card) select karein.
2. Upar **"Variables"** tab par click karein.
3. Yahan click on **"New Variable"** ya raw editor use karke apni `.env.example` waali values add karein:
   - `API_SECRET_KEY` = `koi_bhi_strong_password_ya_key` (Yeh key PHP side se match honi chahiye)
   - `MATCH_THRESHOLD` = `0.55`
   - `MAX_UPLOAD_SIZE_MB` = `10`
   - `ALLOWED_ORIGINS` = `https://your-php-website.com` (Apni PHP website ka URL daalein)
   
*Note: `DATABASE_URL` add karne ki zaroorat nahi hai agar aap Railway ka ephemeral (temporary) file system use kar rahe hain test karne ke liye. Railway default folder structure mein SQLite DB bana dega.*

## Step 4: Persistent Storage (Volume) Attach Karein - VERY IMPORTANT

Kyunki SQLite database (`faces.db`) locally save hota hai, agar Railway server restart hua toh data delete ho jayega. Data bachane ke liye aapko Volume add karna hoga.

1. Apni service settings mein jayein (**Settings** tab).
2. Niche scroll karke **"Volumes"** section dhoondein.
3. **"Add Volume"** par click karein.
4. Mount Path mein `/app/data` likhein. (Kyunki code mein path `./data/faces.db` hai).
5. Yeh karne se container ke andar ka `/app/data` folder safe rahega, restarts ke baad bhi faces delete nahi honge.

## Step 5: Start Command aur Build (Optional Check)

Humne project mein `Procfile` aur `railway.json` pehle se bana diya hai. Railway automatically inko detect kar lega.
Agar aap check karna chahte hain:
1. **Settings** tab mein jayein.
2. **Build** section mein builder "Nixpacks" hona chahiye.
3. **Deploy** section mein Custom Start Command field blank chhod dein (woh `Procfile` se `uvicorn app.main:app --host 0.0.0.0 --port $PORT` utha lega).

## Step 6: Public URL Generate Karein

Railway default roop se API ko bahar access nahi deta. Public link banana padega.
1. **Settings** tab mein jayein.
2. **Networking** section dhoondein.
3. **"Generate Domain"** par click karein.
4. Railway aapko ek link dega jaise `https://face-reco-production.up.railway.app`. Yeh aapka API URL hai!

## Step 7: Test Karein

Ab aap Postman ya apni PHP website se test kar sakte hain.

- **URL**: `https://<apka-railway-domain>/health`
  - Method: `GET`
  - Expected Output: `{"status": "healthy", "service": "face-recognition-api"}`

- **URL**: `https://python-face-reco-production.up.railway.app/api/faces/count`
  - Method: `GET`
  - Headers:
    - `X-API-Key`: `apni_secret_key_jo_step_3_mein_daali`
  - Expected Output: `{"success":true,"total_registered_faces":0}`
