$body = @{ username="testusertest"; password="Test123456" } | ConvertTo-Json
$headers = @{ "Content-Type" = "application/json" }
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login/" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
Write-Output "Status: $($response.StatusCode)"
Write-Output "Body: $($response.Content)"
