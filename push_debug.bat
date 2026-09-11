@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== PUSHING DEBUG VERSION =====
git add routes/rgpd.py

git commit -m "Add debug logging to RGPD export endpoint"
git push origin main

echo.
echo Done! Render will redeploy.
echo.
echo After deploy, call this to check configuration:
echo GET https://stockpredi-backend.onrender.com/api/rgpd/debug
echo.
pause
