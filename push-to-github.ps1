# StockPredi Backend - Push to GitHub & Deploy
# This script pushes your local commits to GitHub
# Render will auto-deploy from GitHub (1-2 min)

Write-Host "StockPredi Backend Deployment Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Git not found. Please install Git for Windows." -ForegroundColor Red
    exit 1
}

# Current directory
$repoPath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Repository: $repoPath" -ForegroundColor Green
Write-Host ""

# Navigate to repo
Set-Location $repoPath
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Gray
Write-Host ""

# Check git status
Write-Host "Git Status:" -ForegroundColor Cyan
git status --short
Write-Host ""

# Show commits to push
Write-Host "Commits to push:" -ForegroundColor Cyan
$commits = git log --oneline origin/main..HEAD -5 2>$null
if ($commits) {
    Write-Host $commits
} else {
    git log --oneline -5
}
Write-Host ""

# Confirm before pushing
Write-Host "Ready to push commits to GitHub?" -ForegroundColor Yellow
$confirm = Read-Host "Continue? (y/n)"

if ($confirm -ne "y") {
    Write-Host "Deployment cancelled." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
Write-Host ""

# Push to GitHub
git push 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Push successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Render will auto-deploy in 1-2 minutes..." -ForegroundColor Cyan
    Write-Host "Dashboard: https://dashboard.render.com/web/srv-d93r28lckfvc73924c90/deploys" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Test endpoints once deployed:" -ForegroundColor Cyan
    Write-Host "  POST https://stockpredi-backend.onrender.com/api/auth/forgot-password" -ForegroundColor Gray
    Write-Host "  POST https://stockpredi-backend.onrender.com/api/auth/reset-password" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "Push failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - Check your internet connection" -ForegroundColor Gray
    Write-Host "  - Check GitHub credentials in Windows Credential Manager" -ForegroundColor Gray
    exit 1
}

Write-Host "Done!" -ForegroundColor Green
