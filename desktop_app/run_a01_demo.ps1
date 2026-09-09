param(
    [switch]$SelfTest,
    [string]$ProjectRoot = "E:\Pose2SimProjects\Badminton_Final"
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $AppRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -eq $PythonLauncher) {
        throw "Python 3 was not found. Install Python 3.10+ from python.org, then run this command again."
    }
    & py -3 -m venv (Join-Path $AppRoot ".venv")
}

& $VenvPython -c "import cv2, PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing the desktop player's local dependencies..." -ForegroundColor Cyan
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $AppRoot "requirements.txt")
}

$Arguments = @(
    (Join-Path $AppRoot "player.py"),
    "--project-root", $ProjectRoot
)
if ($SelfTest) { $Arguments += "--self-test" }

& $VenvPython @Arguments
