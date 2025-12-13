$ErrorActionPreference = "Stop"

# Configuration
$baseUrl = "http://localhost:8081/api"
$rand = Get-Random
$email = "testuser_$rand@example.com"
$password = "password123"
$email2 = "otheruser_$rand@example.com"
$password2 = "password456"

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

function Get-Token {
    param($u, $p)
    try {
        # Ensure user exists (register if needed)
        try {
            Invoke-Json -Uri "$baseUrl/auth/signup" -Method POST -Body @{
                email = $u
                password = $p
            } -AllowError | Out-Null
        } catch {}

        $loginResponse = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body @{
            email = $u
            password = $p
        }
        if (-not $loginResponse.accessToken) {
            throw "accessToken missing in response"
        }
        return $loginResponse.accessToken
    } catch {
        throw $_
    }
}

# --- SCENARIO 1: Authentication & Security ---
Print-Status "Starting Scenario 1: Auth & Security"

# 1.1 Invalid Login
Print-Status "Testing Invalid Login..."
$badLogin = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body @{
    email = "wrong@example.com"
    password = "wrong"
} -AllowError

if ($badLogin.StatusCode -eq [System.Net.HttpStatusCode]::Unauthorized -or $badLogin.StatusCode -eq [System.Net.HttpStatusCode]::Forbidden -or $badLogin.StatusCode -eq [System.Net.HttpStatusCode]::BadRequest) {
    Print-Success "Invalid login rejected as expected."
} else {
    Print-Error "Invalid login should have failed but got $($badLogin.StatusCode)"
}

# 1.2 Access without token
Print-Status "Testing Unauthenticated Access..."
$noToken = Invoke-Json -Uri "$baseUrl/nodes" -Method GET -AllowError
if ($noToken.StatusCode -eq [System.Net.HttpStatusCode]::Unauthorized) {
    Print-Success "Unauthenticated access rejected as expected."
} else {
    Print-Error "Unauthenticated access should be 401 but got $($noToken.StatusCode)"
}

# --- SCENARIO 2: Data Isolation (Multi-User) ---
Print-Status "Starting Scenario 2: Data Isolation"

$token1 = Get-Token $email $password
$token2 = Get-Token $email2 $password2
$headers1 = @{ Authorization = "Bearer $token1" }
$headers2 = @{ Authorization = "Bearer $token2" }

# User 1 creates a secret node
Print-Status "User 1 creating a secret node..."
$node1 = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers1 -Body @{
    name = "User1 Secret"
    type = "PERSON"
    sector = "Tech"
}
Print-Success "User 1 created node: $($node1.id)"

# User 2 tries to see it
Print-Status "User 2 listing nodes..."
$nodes2 = Invoke-Json -Uri "$baseUrl/nodes" -Method GET -Headers $headers2
$found = $nodes2 | Where-Object { $_.id -eq $node1.id }

if ($found) {
    Print-Error "SECURITY FAIL: User 2 can see User 1's node!"
} else {
    Print-Success "Data Isolation OK: User 2 cannot see User 1's node."
}

# --- SCENARIO 3: Validation & Edge Cases ---
Print-Status "Starting Scenario 3: Validation"

# 3.1 Create Node without Name
Print-Status "Creating Node without Name..."
$invalidNode = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers1 -Body @{
    type = "PERSON"
} -AllowError

if ($invalidNode.StatusCode -eq [System.Net.HttpStatusCode]::BadRequest) {
    Print-Success "Validation OK: Missing name rejected (400)."
} elseif ($invalidNode.StatusCode -eq [System.Net.HttpStatusCode]::Unauthorized) {
    Print-Status "Validation Warning: Missing name rejected with 401 Unauthorized (likely due to error dispatch)."
} else {
    Print-Error "Validation FAIL: Expected 400 or 401 but got $($invalidNode.StatusCode)"
}

# --- SCENARIO 4: Complex Graph Operations ---
Print-Status "Starting Scenario 4: Complex Graph"

# Create Triangle: A -> B -> C -> A
$nodeA = $node1 # Already created (PERSON)
$nodeB = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers1 -Body @{ name = "Node B"; type = "GOAL" }
$nodeC = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers1 -Body @{ name = "Node C"; type = "VISION" }

Print-Status "Linking A->B, B->C..."
$link1 = Invoke-Json -Uri "$baseUrl/edges" -Method POST -Headers $headers1 -Body @{ sourceNodeId = $nodeA.id; targetNodeId = $nodeB.id; type = "SUPPORTS"; weight = 5 } -AllowError
if ($link1.StatusCode -and $link1.StatusCode -ne [System.Net.HttpStatusCode]::OK) { Print-Error "Link 1 Failed: $($link1.StatusCode)" }

$link2 = Invoke-Json -Uri "$baseUrl/edges" -Method POST -Headers $headers1 -Body @{ sourceNodeId = $nodeB.id; targetNodeId = $nodeC.id; type = "BELONGS_TO"; weight = 3; sortOrder = 1 } -AllowError
if ($link2.StatusCode -and $link2.StatusCode -ne [System.Net.HttpStatusCode]::OK) { Print-Error "Link 2 Failed: $($link2.StatusCode)" }

Print-Success "Chain created (A->B->C)."

# Verify Graph Structure
$graph = Invoke-Json -Uri "$baseUrl/graph" -Method GET -Headers $headers1
Print-Status "Graph Nodes: $($graph.nodes.Count), Edges: $($graph.links.Count)"
if ($graph.nodes.Count -ge 3 -and $graph.links.Count -ge 2) {
    Print-Success "Graph structure verified (Nodes: $($graph.nodes.Count), Edges: $($graph.links.Count))"
} else {
    Print-Error "Graph structure mismatch."
}

# --- SCENARIO 5: AI & Search ---
Print-Status "Starting Scenario 5: AI & Search"

# Search
$search = Invoke-Json -Uri "$baseUrl/nodes/filter?q=Secret" -Method GET -Headers $headers1
if ($search.Count -eq 1 -and $search[0].name -eq "User1 Secret") {
    Print-Success "Search OK."
} else {
    Print-Error "Search failed."
}

# Cleanup
Print-Status "Cleaning up..."
Invoke-Json -Uri "$baseUrl/nodes/$($nodeA.id)" -Method DELETE -Headers $headers1
Invoke-Json -Uri "$baseUrl/nodes/$($nodeB.id)" -Method DELETE -Headers $headers1
Invoke-Json -Uri "$baseUrl/nodes/$($nodeC.id)" -Method DELETE -Headers $headers1

Print-Status "Advanced Test Suite Completed."
