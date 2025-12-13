
$baseUrl = "http://localhost:8081/api"
$authUrl = "$baseUrl/auth/signin"
$graphUrl = "$baseUrl/graph"

# 1. Login
$loginBody = @{
    email = "testuser@example.com"
    password = "password123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri $authUrl -Method Post -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.accessToken
    $headers = @{ Authorization = "Bearer $token" }
    Write-Host "[+] Login successful."
} catch {
    Write-Error "Login failed. Make sure the backend is running."
    exit 1
}

# 2. Create some nodes to ensure we have enough data
Write-Host "Creating 5 test nodes..."
for ($i = 1; $i -le 5; $i++) {
    $nodeBody = @{
        type = "PERSON"
        name = "LimitTest User $i"
        description = "Testing limit parameter"
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "$baseUrl/nodes" -Method Post -Body $nodeBody -Headers $headers -ContentType "application/json" | Out-Null
    } catch {
        Write-Warning "Failed to create node $i"
    }
}

# 3. Test Limit Parameter
$limit = 3
$uri = "$graphUrl`?limit=$limit"
Write-Host "Fetching graph from: $uri"
try {
    $graphResponse = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers
    $nodeCount = $graphResponse.nodes.Count
    
    Write-Host "Nodes returned: $nodeCount"
    
    if ($nodeCount -eq $limit) {
        Write-Host "[SUCCESS] The API returned exactly $limit nodes as requested." -ForegroundColor Green
    } elseif ($nodeCount -lt $limit) {
         Write-Host "[WARNING] The API returned fewer nodes ($nodeCount) than the limit ($limit). This is valid if total nodes are fewer than limit." -ForegroundColor Yellow
    } else {
        Write-Host "[FAILURE] The API returned $nodeCount nodes, but limit was $limit." -ForegroundColor Red
        exit 1
    }

} catch {
    Write-Error "Failed to fetch graph: $_"
    exit 1
}
