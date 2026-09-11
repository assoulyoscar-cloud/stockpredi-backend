@echo off
setlocal enabledelayedexpansion

cd /d C:\Users\Oscar\stockpredi-backend

echo ===== FIXING RGPD ROUTE PATHS =====
echo.

REM Read the file and apply fixes using PowerShell
powershell -NoProfile -Command ^
  "$content = Get-Content 'routes\rgpd.py' -Raw; " ^
  "$content = $content -replace \"@rgpd_bp\.route\('/api/rgpd/debug'\", \"@rgpd_bp.route('/debug'\"; " ^
  "$content = $content -replace \"@rgpd_bp\.route\('/api/rgpd/export'\", \"@rgpd_bp.route('/export'\"; " ^
  "$content = $content -replace \"@rgpd_bp\.route\('/api/rgpd/status'\", \"@rgpd_bp.route('/status'\"; " ^
  "$content = $content -replace \"@rgpd_bp\.route\('/api/rgpd/delete'\", \"@rgpd_bp.route('/delete'\"; " ^
  "$content = $content -replace \"@rgpd_bp\.route\('/api/rgpd/contact'\", \"@rgpd_bp.route('/contact'\"; " ^
  "Set-Content 'routes\rgpd.py' -Value $content; " ^
  "Write-Host 'Routes fixes appliquees'"

echo.
echo ===== COMMITTING AND PUSHING =====
git add routes/rgpd.py
git commit -m "Fix: correct route paths in RGPD blueprint to avoid double /api/rgpd prefix"
git push origin main

if %errorlevel% eq 0 (
    echo.
    echo ✓ SUCCESS! Changes pushed to GitHub
    echo Render will redeploy automatically...
    echo.
    echo Test the debug endpoint after deployment (1-2 mins):
    echo GET https://stockpredi-backend.onrender.com/api/rgpd/debug
) else (
    echo.
    echo ✗ Git push failed
)

echo.
pause