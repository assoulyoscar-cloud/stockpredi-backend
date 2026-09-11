@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== COMMITTING FIXES =====
git add routes/rgpd.py services/archive_service.py

echo.
echo ===== GIT STATUS =====
git status

echo.
echo ===== PUSHING =====
git commit -m "Fix: Send archive PDF to client email, not owner email - RGPD compliance"
git push origin main

echo.
echo Done!
pause
