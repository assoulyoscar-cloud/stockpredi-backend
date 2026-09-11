@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== ADDING FILES TO GIT =====
git add routes/archive.py
git add services/archive_service.py
git add services/google_drive_service.py

echo.
echo ===== GIT STATUS =====
git status

echo.
echo ===== COMMITTING =====
git commit -m "Add archive service with Google Drive integration and Resend email delivery"

echo.
echo ===== PUSHING TO GITHUB =====
git push origin main

echo.
echo Done!
pause
