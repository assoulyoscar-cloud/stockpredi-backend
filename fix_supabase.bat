@echo off
cd /d C:\Users\Oscar\stockpredi-backend

echo ===== FIXING SUPABASE CLIENT INITIALIZATION =====
git add routes/rgpd.py

echo.
echo ===== COMMITTING =====
git commit -m "Fix: lazy initialize Supabase client to avoid import errors"
git push origin main

echo.
echo Done! Render will redeploy.
pause
