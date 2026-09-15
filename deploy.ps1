# DEPLOY CORS PREFLIGHT FIX
Write-Host "🔧 DEPLOYING CORS PREFLIGHT FIX" -ForegroundColor Cyan
Write-Host ""

# 1. CHECK GIT STATUS
Write-Host "1️⃣  Git Status:" -ForegroundColor Yellow
git status

# 2. ADD & COMMIT
Write-Host "
2️⃣  Staging & Committing:" -ForegroundColor Yellow
git add app.py
git commit -m "Fix: CORS preflight OPTIONS requests handler"

# 3. PUSH
Write-Host "
3️⃣  Pushing to GitHub:" -ForegroundColor Yellow
git push origin main

if (0 -eq 0) {
    Write-Host "
✅ SUCCESS!" -ForegroundColor Green
    Write-Host "⏱️  Render redéploie maintenant (~2-3 min)" -ForegroundColor Cyan
} else {
    Write-Host "
❌ Push failed" -ForegroundColor Red
}
