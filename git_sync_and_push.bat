@echo off
cd /d C:\Users\Oscar\stockpredi-backend
echo Fetching remote changes...
git pull origin main
echo.
echo Pushing to GitHub...
git push origin main
echo.
echo Done!
pause
