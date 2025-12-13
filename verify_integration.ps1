$ErrorActionPreference = "Stop"

# Configuration
$baseUrl = "http://localhost:8081/api"
$rand = Get-Random
$email = "integration_test_$rand@example.com"
$password = "password123"

function Print-Status {
    param([string]$msg)
    Write-Host ("[{0}] {1}" -f (Get-Date).ToString("HH:mm:ss"), $msg) -ForegroundColor Cyan
}

function Print-Success {
    param([string]$msg)
    Write-Host "[+] $msg" -ForegroundColor Green
}

function Print-Error {
    param([string]$msg)
    Write-Host "[-] $msg" -ForegroundColor Red
}

function Invoke-Json {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [hashtable]$Body = $null,
        [switch]$AllowError
    )

    try {
        if ($Body) {
            return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers -Body ($Body | ConvertTo-Json -Depth 10) -ContentType "application/json" -ErrorAction Stop
        }
        return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers -ErrorAction Stop
    } catch {
        if ($AllowError) {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $errContent = $reader.ReadToEnd()
            Write-Host "DEBUG: Error Body: $errContent" -ForegroundColor Yellow
            return $_.Exception.Response
        }
        throw $_
    }
}

Print-Status "Starting Frontend/Mobile Integration Verification..."

# 1. Authentication (Shared by both)
Print-Status "1. Testing Authentication (Frontend/Mobile)"
$authBody = @{
    email = $email
    password = $password
}
Invoke-Json -Uri "$baseUrl/auth/signup" -Method POST -Body $authBody | Out-Null
$loginRes = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body $authBody
$token = $loginRes.accessToken
$headers = @{ Authorization = "Bearer $token" }
Print-Success "Auth successful. Token received."

# 2. Frontend Specific Calls
Print-Status "2. Testing Frontend Specific Calls"

# 2.1 fetchGraph
Print-Status "   - fetchGraph (/api/graph)"
$graph = Invoke-Json -Uri "$baseUrl/graph" -Method GET -Headers $headers
if ($graph.nodes -ne $null -and $graph.links -ne $null) {
    Print-Success "fetchGraph OK (Nodes: $($graph.nodes.Count), Links: $($graph.links.Count))"
} else {
    Print-Error "fetchGraph FAILED: Missing nodes or links property"
}

# 2.2 createNode (Frontend Payload)
Print-Status "   - createNode (Frontend Payload)"
$feNodePayload = @{
    name = "Frontend Node"
    type = "PERSON"
    sector = "IT"
    tags = @("frontend", "react")
    relationshipStrength = 4
}
$feNode = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers -Body $feNodePayload
Print-Success "Frontend Node Created: $($feNode.id)"

# 2.3 searchNodes (Frontend uses /nodes/filter?q=...)
Print-Status "   - searchNodes (/api/nodes/filter?q=Frontend)"
$feSearch = Invoke-Json -Uri "$baseUrl/nodes/filter?q=Frontend" -Method GET -Headers $headers
if ($feSearch.Count -ge 1) {
    Print-Success "Frontend Search OK"
} else {
    Print-Error "Frontend Search FAILED"
}

# 3. Mobile Specific Calls
Print-Status "3. Testing Mobile Specific Calls"

# 3.1 createNode (Mobile Payload - often simpler)
Print-Status "   - createNode (Mobile Payload)"
$mobileNodePayload = @{
    name = "Mobile Node"
    type = "PERSON"
    sector = "Mobile Dev"
    relationshipStrength = 5
}
$mobileNode = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers -Body $mobileNodePayload
Print-Success "Mobile Node Created: $($mobileNode.id)"

# 3.2 getAllNodes (Mobile uses /api/nodes)
Print-Status "   - getAllNodes (/api/nodes)"
$allNodes = Invoke-Json -Uri "$baseUrl/nodes" -Method GET -Headers $headers
if ($allNodes.Count -ge 2) {
    Print-Success "getAllNodes OK (Count: $($allNodes.Count))"
} else {
    Print-Error "getAllNodes FAILED"
}

# 3.3 searchNodes (Mobile uses /api/nodes/filter?q=...)
Print-Status "   - searchNodes (/api/nodes/filter?q=Mobile)"
try {
    $mobileSearch = Invoke-Json -Uri "$baseUrl/nodes/filter?q=Mobile" -Method GET -Headers $headers
    if ($mobileSearch.Count -ge 1) {
        Print-Success "Mobile Search Endpoint OK"
    } else {
        Print-Error "Mobile Search returned no results"
    }
} catch {
    Print-Error "Mobile Search Endpoint FAILED"
}

# 4. Cleanup
Print-Status "4. Cleanup"
Invoke-Json -Uri "$baseUrl/nodes/$($feNode.id)" -Method DELETE -Headers $headers
Invoke-Json -Uri "$baseUrl/nodes/$($mobileNode.id)" -Method DELETE -Headers $headers
Print-Success "Cleanup Done"

Print-Status "Integration Verification Completed."
