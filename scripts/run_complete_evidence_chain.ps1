param(
    [string]$ProjectRoot = "E:\Pose2SimProjects\Badminton_Final",
    [string]$Action = "A01",
    [int]$Repeat = 1,
    [string]$PythonPath = "",
    [switch]$ExecutePose2Sim
)

$ErrorActionPreference = "Stop"
$Repository = Split-Path -Parent $PSScriptRoot
if ($PythonPath) {
    $Python = $PythonPath
} else {
    $Pose2SimPython = Join-Path $env:USERPROFILE ".venv\pose2sim\Scripts\python.exe"
    $RepositoryPython = Join-Path $Repository ".venv\Scripts\python.exe"
    if (Test-Path $Pose2SimPython) { $Python = $Pose2SimPython }
    elseif (Test-Path $RepositoryPython) { $Python = $RepositoryPython }
    else { throw "No Python environment was found. Supply -PythonPath with the Pose2Sim Python executable." }
}
if (-not (Test-Path $Python)) { throw "Python environment not found: $Python" }
$env:PYTHONPATH = Join-Path $Repository "src"
$Output = Join-Path $ProjectRoot ("reports\{0}_R{1:00}_evidence_chain" -f $Action, $Repeat)
$Config = Join-Path $ProjectRoot ("{0}\Config.toml" -f $Action)

& $Python -m badminton_court35 pose2sim --config $Config --stages calibration poseEstimation synchronization triangulation filtering
if ($ExecutePose2Sim) {
    & $Python -m badminton_court35 pose2sim --config $Config --stages calibration poseEstimation synchronization triangulation filtering --execute
}
& $Python -m badminton_court35 build-evidence-chain --project-root $ProjectRoot --action $Action --repeat $Repeat --output-dir $Output --report (Join-Path $Output "command_report.json")
Write-Host "Evidence-chain report: $Output\evidence_chain.json" -ForegroundColor Green
