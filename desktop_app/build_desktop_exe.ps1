$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $AppRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Run .\desktop_app\run_a01_demo.ps1 once before building the executable."
}

& $Python -m pip install pyinstaller
& $Python -m PyInstaller --noconfirm --clean --windowed --name "BadmintonFusion35-Player" --collect-all cv2 --collect-all PIL --distpath (Join-Path $AppRoot "dist") --workpath (Join-Path $AppRoot "build") --specpath $AppRoot (Join-Path $AppRoot "player.py")

Write-Host "Created: $AppRoot\dist\BadmintonFusion35-Player\BadmintonFusion35-Player.exe" -ForegroundColor Green
