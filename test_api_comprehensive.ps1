$ErrorActionPreference = "Stop"

# Configuration
$baseUrl = "http://localhost:8080/api"
$email = "testuser@example.com"
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
        [hashtable]$Body = $null
    )

    if ($Body) {
        return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers -Body ($Body | ConvertTo-Json -Depth 10) -ContentType "application/json"
    }

    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $Headers
}

function Get-Token {
    try {
        $loginResponse = Invoke-Json -Uri "$baseUrl/auth/signin" -Method POST -Body @{
            email = $email
            password = $password
        }
        if (-not $loginResponse.accessToken) {
            throw "accessToken missing in response"
        }
        return $loginResponse.accessToken
    } catch {
        throw $_
    }
}

$headers = @{}

# 1. Login / Sign up if necessary
Print-Status "Ensuring test user exists..."
try {
    $token = Get-Token
} catch {
    Print-Status "User not found. Attempting to register..."
    try {
        Invoke-Json -Uri "$baseUrl/auth/signup" -Method POST -Body @{
            email = $email
            password = $password
        } | Out-Null
        Start-Sleep -Seconds 1
        $token = Get-Token
    } catch {
        Print-Error "Unable to sign up or login: $_"
        exit 1
    }
}

$headers = @{
    Authorization = "Bearer $token"
}
Print-Success "Authentication ready."

# 2. Create Person Node
Print-Status "Creating Person node..."
try {
    $person = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers -Body @{
        type = "PERSON"
        name = "John Doe"
        description = "Backend engineer"
        sector = "Technology"
        tags = @("developer", "engineer")
        relationshipStrength = 4
        company = "Tech Corp"
        properties = @{
            role = "Senior Engineer"
            experienceYears = 8
        }
    }

    if (-not $person.id) {
        throw "Person node creation failed"
    }
    Print-Success "Person created: $($person.name) ($($person.id))"
} catch {
    Print-Error "Failed to create person node: $_"
    exit 1
}

# 3. Create Goal Node
Print-Status "Creating Goal node..."
try {
    $goal = Invoke-Json -Uri "$baseUrl/nodes" -Method POST -Headers $headers -Body @{
        type = "GOAL"
        name = "MVP Launch"
        description = "Prepare MVP launch plan"
        priority = 4
        dueDate = "2025-06-30"
        tags = @("launch", "product")
    }

    if (-not $goal.id) {
        throw "Goal node creation failed"
    }
    Print-Success "Goal created: $($goal.name) ($($goal.id))"
} catch {
    Print-Error "Failed to create goal node: $_"
    exit 1
}

# 4. Create SUPPORTS Edge (Person -> Goal)
Print-Status "Linking person to goal via SUPPORTS edge..."
try {
    $edge = Invoke-Json -Uri "$baseUrl/edges" -Method POST -Headers $headers -Body @{
        sourceNodeId = $person.id
        targetNodeId = $goal.id
        type = "SUPPORTS"
        weight = 4
        relationshipStrength = 4
        relevanceScore = 0.82
        notes = "Leading backend stream"
    }

    if (-not $edge.id) {
        throw "Edge creation failed"
    }
    Print-Success "Edge created: $($edge.id)"
} catch {
    Print-Error "Failed to create edge: $_"
    exit 1
}

# 5. Fetch Graph
Print-Status "Fetching graph..."
try {
    $graph = Invoke-Json -Uri "$baseUrl/graph" -Headers $headers
    $nodeCount = $graph.nodes.Count
    $edgeCount = $graph.links.Count

    if ($nodeCount -ge 2 -and $edgeCount -ge 1) {
        Print-Success "Graph OK. Nodes: $nodeCount, Edges: $edgeCount"
    } else {
        Print-Error "Unexpected graph counts. Nodes: $nodeCount, Edges: $edgeCount"
    }
} catch {
    Print-Error "Failed to fetch graph: $_"
}

# 6. Update Person Node
Print-Status "Updating person node..."
try {
    $updatedPerson = Invoke-Json -Uri "$baseUrl/nodes/$($person.id)" -Method PUT -Headers $headers -Body @{
        type = "PERSON"
        name = "Johnathan Doe"
        description = "Backend engineer - promoted"
        sector = "Technology"
        tags = @("developer", "engineer", "mentor")
        relationshipStrength = 5
    }

    if ($updatedPerson.name -eq "Johnathan Doe") {
        Print-Success "Person node updated."
    } else {
        Print-Error "Person update response unexpected."
    }
} catch {
    Print-Error "Failed to update person node: $_"
}

# 7. Filter Nodes
Print-Status "Filtering nodes by search term 'MVP'..."
try {
    $filteredNodes = Invoke-Json -Uri "$baseUrl/nodes/filter?q=MVP" -Headers $headers
    $count = ($filteredNodes | Measure-Object).Count
    if ($count -gt 0) {
        Print-Success "Filter returned $count node(s)."
    } else {
        Print-Error "Filter returned no nodes."
    }
} catch {
    Print-Error "Failed to filter nodes: $_"
}

# 8. Delete Edge
Print-Status "Deleting edge..."
try {
    Invoke-RestMethod -Uri "$baseUrl/edges/$($edge.id)" -Method DELETE -Headers $headers | Out-Null
    Print-Success "Edge deleted."
} catch {
    Print-Error "Failed to delete edge: $_"
}

# 9. Delete nodes
Print-Status "Deleting goal node..."
try {
    Invoke-RestMethod -Uri "$baseUrl/nodes/$($goal.id)" -Method DELETE -Headers $headers | Out-Null
    Print-Success "Goal node deleted."
} catch {
    Print-Error "Failed to delete goal node: $_"
}

Print-Status "Deleting person node..."
try {
    Invoke-RestMethod -Uri "$baseUrl/nodes/$($person.id)" -Method DELETE -Headers $headers | Out-Null
    Print-Success "Person node deleted."
} catch {
    Print-Error "Failed to delete person node: $_"
}

Print-Status "Test suite completed."
