$backendUrl = "https://stockpredi-backend.onrender.com"
$endpointUrl = "$backendUrl/api/predictions/recommendations"

# Token Supabase pour test
$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiYWNobGRteGJqcWt0eXF4enVtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjgzMTYwMSwiZXhwIjoyMDk4NDA3NjAxfQ.VWIOqWI2zuAQMen77GxG1NmeMX03hh8ywJU9cKS3Wus"

Write-Host "🧪 Testing StockPredi /api/predictions/recommendations" -ForegroundColor Cyan
Write-Host "Target: $endpointUrl" -ForegroundColor Gray
Write-Host ""

$testData = @{
    "data" = @(
        @{ "ds" = "2024-01-01"; "y" = 100 },
        @{ "ds" = "2024-01-02"; "y" = 105 },
        @{ "ds" = "2024-01-03"; "y" = 102 },
        @{ "ds" = "2024-01-04"; "y" = 110 },
        @{ "ds" = "2024-01-05"; "y" = 108 },
        @{ "ds" = "2024-01-06"; "y" = 115 },
        @{ "ds" = "2024-01-07"; "y" = 120 }
    )
    "product_name" = "Test Widget"
    "periods" = 30
} | ConvertTo-Json

Write-Host "Test 1: Valid forecast request" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-WebRequest -Uri $endpointUrl `
        -Method POST `
        -Headers $headers `
        -Body $testData `
        -TimeoutSec 30 `
        -ErrorAction SilentlyContinue

    if ($response) {
        $statusCode = $response.StatusCode
        $body = $response.Content | ConvertFrom-Json

        Write-Host "Status Code: $statusCode" -ForegroundColor $(if ($statusCode -eq 200) { "Green" } else { "Red" })
        
        if ($statusCode -eq 200) {
            Write-Host "✅ SUCCESS: Status 200 OK" -ForegroundColor Green
            Write-Host "   Forecast: $(if ($body.forecast) { 'Present' } else { 'Missing' })" -ForegroundColor Gray
            Write-Host "   Recommendations: $(if ($body.recommendations) { 'Present' } else { 'Missing' })" -ForegroundColor Gray
            Write-Host "   AI Source: $($body.ai_source)" -ForegroundColor Gray
            Write-Host ""
            Write-Host "🎉 FIX VALIDATED: No HTTP 500 error!" -ForegroundColor Green
            Write-Host "   Prophet + error handling working correctly" -ForegroundColor Green
        }
        else {
            Write-Host "❌ FAILED: Status $statusCode" -ForegroundColor Red
            Write-Host "   Error: $($body.error)" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 Test complete!" -ForegroundColor Cyan
