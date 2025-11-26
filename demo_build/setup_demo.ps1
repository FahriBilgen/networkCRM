#requires -Version 5.0
param()

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$VenvDir = Join-Path $ScriptRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$StartUrl = "http://localhost:8000/"

function Resolve-Python {
    # Prefer the py launcher when present; otherwise fall back to python3/python
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @{ Path = $pyCmd.Source; UsePy = $true }
    }

    $candidates = @("python3", "python")
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return @{ Path = $command.Source; UsePy = $false }
        }
    }

    throw "Python 3 is required but was not found on PATH."
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "`n[demo] Creating virtual environment at $VenvDir"
    $pythonInfo = Resolve-Python
    if ($pythonInfo.UsePy) {
        & $pythonInfo.Path -3 -m venv $VenvDir
    } else {
        & $pythonInfo.Path -m venv $VenvDir
    }
}

Write-Host "`n[demo] Installing Python dependencies"
& $VenvPython -m pip install --upgrade pip | Out-Null
& $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "`n[demo] Ollama detected. Running health check..."
    try {
        ollama list | Out-Null
    } catch {
        Write-Warning "Ollama is installed but unreachable. Demo will rely on scripted fallbacks."
    }
} else {
    Write-Warning "Ollama is not installed. Demo will use scripted fallbacks."
}

$modelScript = Join-Path $RepoRoot "scripts\download_models.sh"
if (Test-Path $modelScript) {
    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if ($bash) {
        Write-Host "`n[demo] Ensuring demo models are available"
        & $bash.Source $modelScript
    } else {
        Write-Warning "bash is not available; skipping model download script."
    }
} else {
    Write-Warning "$modelScript is missing; skipping model download."
}

$uiDir = Join-Path $RepoRoot "fortress_director\demo\web"
if (-not (Test-Path $uiDir)) {
    throw "UI directory $uiDir not found."
}

Write-Host "`n[demo] Installing UI dependencies"
Push-Location $uiDir
npm install
Write-Host "[demo] Building UI bundle"
npm run build
# If the build produced a local `dist` directory (older configs), copy it to demo_build/ui_dist
$localDist = Join-Path $uiDir "dist"
if (Test-Path $localDist) {
    Write-Host "[demo] Copying local dist to demo_build/ui_dist"
    $target = Join-Path $RepoRoot "demo_build\ui_dist"
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item -Path (Join-Path $localDist "*") -Destination $target -Recurse -Force
}
Pop-Location

Write-Host "`n[demo] Starting backend server (Ctrl+C to stop)"
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process $using:StartUrl
} | Out-Null

& $VenvPython -m uvicorn fortress_director.api:app --host 0.0.0.0 --port 8000
