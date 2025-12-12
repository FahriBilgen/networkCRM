$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8081/api"
$email = "aie2e@example.com"
$password = "password123"

function Invoke-Json {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [hashtable]$Body = $null
    )
    if ($Body) {
        return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers -Body ($Body | ConvertTo-Json -Depth 10) -ContentType "application/json"
    }
    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers
}

function Ensure-Token {
    param([string]$Email, [string]$Password)
    $loginBody = @{ email = $Email; password = $Password }
    try {
        $resp = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body $loginBody
        return $resp.accessToken
    } catch {
        Invoke-Json -Uri "$baseUrl/auth/signup" -Method POST -Body $loginBody | Out-Null
        Start-Sleep -Seconds 1
        $resp = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body $loginBody
        return $resp.accessToken
    }
}

$token = Ensure-Token -Email $email -Password $password
$headers = @{ Authorization = "Bearer $token" }

Write-Host "[AI-E2E] Token acquired." -ForegroundColor Cyan

function Create-Node {
    param([hashtable]$Payload)
    return Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers -Body $Payload
}

$person1 = Create-Node -Payload @{
    type = "PERSON"
    name = "Fintech Mentor"
    description = "Experienced mentor in fintech scaling partners"
    sector = "Fintech"
    tags = @("mentor", "fintech")
    relationshipStrength = 4
    notes = "Knows key investors"
}

$person2 = Create-Node -Payload @{
    type = "PERSON"
    name = "Growth Advisor"
    description = "Helps with GTM and partnerships"
    sector = "Marketing"
    tags = @("growth", "advisor")
    relationshipStrength = 3
    notes = "Works with SaaS startups"
}

$goal = Create-Node -Payload @{
    type = "GOAL"
    name = "Expand fintech pipeline"
    description = "Need intros to seed fintech investors"
    priority = 5
    tags = @("fintech", "pipeline")
}

Write-Host "[AI-E2E] Created sample nodes: $($person1.id), $($person2.id), goal $($goal.id)" -ForegroundColor Green

$aiResponse = Invoke-Json -Uri "$baseUrl/ai/goals/$($goal.id)/suggestions?limit=5" -Headers $headers

Write-Host "[AI-E2E] Suggestions Response:" -ForegroundColor Cyan
$aiResponse | ConvertTo-Json -Depth 6 | Write-Output

# cleanup
Invoke-RestMethod -Uri "$baseUrl/nodes/$($person1.id)" -Method DELETE -Headers $headers | Out-Null
Invoke-RestMethod -Uri "$baseUrl/nodes/$($person2.id)" -Method DELETE -Headers $headers | Out-Null
Invoke-RestMethod -Uri "$baseUrl/nodes/$($goal.id)" -Method DELETE -Headers $headers | Out-Null
