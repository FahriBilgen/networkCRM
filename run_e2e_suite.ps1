$ErrorActionPreference = "Stop"

Write-Host "Starting Backend..."
Set-Location backend-java
$proc = Start-Process java -ArgumentList "-jar", "target/network-crm-0.0.1-SNAPSHOT.jar", "--spring.profiles.active=dev" -PassThru -NoNewWindow -RedirectStandardOutput "backend.log" -RedirectStandardError "backend.err"

Write-Host "Backend started with PID $($proc.Id). Waiting 20 seconds for startup..."
Start-Sleep -Seconds 20

Set-Location ..

Write-Host "Running E2E Tests..."
try {
    ./test_api_advanced.ps1
}
catch {
    Write-Error "Tests failed: $_"
}
finally {
    Write-Host "Stopping Backend..."
    Stop-Process -InputObject $proc -Force
    Write-Host "Backend stopped."
    
    Write-Host "Backend Logs (Last 50 lines):"
    Get-Content backend-java/backend.log -Tail 50
    
    Write-Host "Backend Errors:"
    Get-Content backend-java/backend.err
}
