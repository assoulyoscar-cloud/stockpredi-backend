@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== VERIFICATION DES FICHIERS =====
echo.
echo Checking routes/archive.py:
if exist routes\archive.py (echo [OK] archive.py exists) else (echo [MISSING] archive.py NOT FOUND)

echo.
echo Checking services/google_drive_service.py:
if exist services\google_drive_service.py (echo [OK] google_drive_service.py exists) else (echo [MISSING] google_drive_service.py NOT FOUND)

echo.
echo Checking services/archive_service.py:
if exist services\archive_service.py (echo [OK] archive_service.py exists) else (echo [MISSING] archive_service.py NOT FOUND)

echo.
echo ===== GIT STATUS =====
git status

pause
