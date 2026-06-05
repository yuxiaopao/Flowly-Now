# Login and save token
$loginBody = @{
    username = "testusertest"
    password = "Test123456"
} | ConvertTo-Json

Write-Output "Logging in as testusertest..."
try {
    $login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login/" -Method POST -Body $loginBody -ContentType "application/json" -TimeoutSec 30
    $token = $login.access
    Write-Output "Login SUCCESS"
    Write-Output "Token prefix: $($token.Substring(0, [Math]::Min(20, $token.Length)))..."
} catch {
    Write-Output "Login FAILED: $($_.Exception.Message)"
    exit 1
}

# Save token
$token | Out-File "e:\Flowly-now\test_token.txt" -NoNewline
