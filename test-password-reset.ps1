# Test password reset endpoints

Write-Host "Testing Password Reset Endpoints" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://stockpredi-backend.onrender.com"
$testEmail = "test@example.com"

Write-Host "1. Testing forgot-password endpoint..." -ForegroundColor Yellow
$body = @{ email = $testEmail } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "$baseUrl/api/auth/forgot-password" `
  -Method POST `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body `
  -SkipHttpErrorCheck

if ($response.StatusCode -eq 200) {
    Write-Host "✓ forgot-password: 200 OK" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | Format-List
} else {
    Write-Host "✗ forgot-password: $($response.StatusCode)" -ForegroundColor Red
    $response.Content
}

Write-Host ""
Write-Host "2. Testing reset-password endpoint..." -ForegroundColor Yellow
$body = @{ 
    access_token = "test_token_12345"
    new_password = "newpass123456"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "$baseUrl/api/auth/reset-password" `
  -Method POST `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body `
  -SkipHttpErrorCheck

if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 400) {
    Write-Host "✓ reset-password responding (code: $($response.StatusCode))" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | Format-List
} else {
    Write-Host "✗ reset-password: $($response.StatusCode)" -ForegroundColor Red
    $response.Content
}

Write-Host ""
Write-Host "3. Testing health endpoint..." -ForegroundColor Yellow
$response = Invoke-WebRequest -Uri "$baseUrl/health" -SkipHttpErrorCheck
Write-Host "Backend status: $($response.StatusCode)" -ForegroundColor Green
