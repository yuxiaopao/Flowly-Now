param([string]$Token)
$headers = @{ Authorization = "Bearer $Token" }

Write-Output "=== Test 1: List Available Models ==="
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/gateway/models/available/?type=chat" -Method GET -Headers $headers -TimeoutSec 30
    Write-Output "Status: SUCCESS"
    Write-Output "Models found: $($r.Count)"
    $r | ForEach-Object { Write-Output "  - [$($_.provider)] $($_.name) (id: $($_.model_id))" }
} catch {
    Write-Output "Status: FAILED - $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== Test 2: List NL-Specific Models ==="
try {
    $r2 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nl-workflow/models/" -Method GET -Headers $headers -TimeoutSec 30
    Write-Output "Status: SUCCESS"
    Write-Output "Default model: $($r2.default)"
    Write-Output "Models found: $($r2.models.Count)"
    $r2.models | ForEach-Object { Write-Output "  - [$($_.provider)] $($_.name) (id: $($_.model_id))" }
} catch {
    Write-Output "Status: FAILED - $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== Test 3: Create NL Session with Ollama model ==="
try {
    $body = @{
        description = "Create a simple workflow: get user input and return a greeting"
        name = "Test NL Session $(Get-Date -Format 'yyyyMMdd-HHmmss')"
        model = "qwen2.5-coder:7b"
        temperature = 0.7
    } | ConvertTo-Json
    $r3 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nl-workflow/sessions/" -Method POST -Headers $headers -Body $body -ContentType "application/json" -TimeoutSec 180
    Write-Output "Status: SUCCESS"
    Write-Output "Session ID: $($r3.session_id)"
    Write-Output "Message: $($r3.message)"
    if ($r3.workflow) {
        Write-Output "Workflow Name: $($r3.workflow.name)"
        Write-Output "Nodes: $($r3.workflow.nodes.Count)"
        Write-Output "Node types: $($r3.workflow.nodes.type -join ', ')"
    }
    if ($r3.error) {
        Write-Output "ERROR: $($r3.error)"
    }
    $script:sessionId = $r3.session_id
} catch {
    Write-Output "Status: FAILED - $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== Test 4: Get Session Detail ==="
if ($sessionId) {
    try {
        $r4 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nl-workflow/sessions/$sessionId/" -Method GET -Headers $headers -TimeoutSec 30
        Write-Output "Status: SUCCESS"
        Write-Output "Session name: $($r4.name)"
        Write-Output "Workflow JSON present: $(-not [string]::IsNullOrEmpty($r4.workflow_json))"
    } catch {
        Write-Output "Status: FAILED - $($_.Exception.Message)"
    }
} else {
    Write-Output "Skipped (no session ID)"
}

Write-Output ""
Write-Output "=== Test 5: Get Sessions List ==="
try {
    $r5 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/nl-workflow/sessions/" -Method GET -Headers $headers -TimeoutSec 30
    Write-Output "Status: SUCCESS"
    Write-Output "Sessions count: $($r5.Count)"
} catch {
    Write-Output "Status: FAILED - $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== ALL TESTS COMPLETED ==="
