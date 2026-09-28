# Deploy DigiRoom for free (Render + Neon)

## 1. Free database (Neon)
1. Sign up at https://neon.tech (free, no card) -> Create project.
2. Copy the **connection string** (starts with `postgresql://...`).

## 2. Push code to GitHub
Copy these changed files into your repo (charmimehta03/DigiRoom) and push:
app.py, requirements.txt, render.yaml, .python-version, .gitignore, DEPLOY.md,
backend/database/database.py, frontend/js/webrtc_teacher.js, frontend/js/webrtc_student.js

## 3. Free web host (Render)
1. Sign up at https://render.com with GitHub.
2. New + -> Blueprint (or Web Service) -> select the DigiRoom repo.
3. If Web Service: Build `pip install -r requirements.txt`,
   Start `uvicorn app:app --host 0.0.0.0 --port $PORT`, Plan: Free.
4. Environment -> add `DATABASE_URL` = your Neon string, `PYTHON_VERSION` = 3.12.7.
5. Deploy. Your site: https://<name>.onrender.com

## Notes
- Free Render sleeps after ~15 min idle; first open takes ~30-60 s.
  (Optional: ping /health every 10 min with https://uptimerobot.com)
- Camera/mic need HTTPS - Render provides it.
- Uploaded files (recordings, PPTs) live on Render's temporary disk and are
  wiped on redeploy/restart. Accounts, lectures, chat, polls are safe in Neon.
