@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== FIXING REQUIREMENTS.TXT =====
git add requirements.txt

echo.
echo ===== COMMITTING =====
git commit -m "Fix: ensure google-auth packages in requirements.txt"
git push origin main

echo.
echo Done! Render will redeploy automatically.
pause
