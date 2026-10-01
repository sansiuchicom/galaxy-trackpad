# Build Galaxy Trackpad Windows onedir (Phase 4B)
# Usage (from repo root):
#   powershell -File packaging\build_windows.ps1
#
# Prefers the galaxytrackpad conda env so PySide6 is actually bundled.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Resolve-BuildPython {
    $candidates = @(
        "$env:USERPROFILE\anaconda3\envs\galaxytrackpad\python.exe",
        "$env:USERPROFILE\miniconda3\envs\galaxytrackpad\python.exe",
        "$env:LOCALAPPDATA\anaconda3\envs\galaxytrackpad\python.exe",
        "$env:LOCALAPPDATA\miniconda3\envs\galaxytrackpad\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if ($conda) {
        try {
            $prefix = (& conda info --envs 2>$null | Select-String "^\s*galaxytrackpad\s").ToString()
            if ($prefix -match '([A-Za-z]:\\[^\s]+)') {
                $p = Join-Path $Matches[1] "python.exe"
                if (Test-Path $p) { return $p }
            }
        } catch {}
    }
    return (Get-Command python).Source
}

$Py = Resolve-BuildPython
Write-Host "Repo: $Root"
Write-Host "Python: $Py"

& $Py -c "import PySide6, websockets; print('PySide6', PySide6.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "This Python is missing PySide6/websockets. Activate galaxytrackpad (conda activate galaxytrackpad) or install requirements.txt, then rebuild."
}

Write-Host "Installing PyInstaller if needed..."
& $Py -m pip install -q "pyinstaller>=6.3,<7"

Write-Host "Cleaning previous dist/build..."
Remove-Item -Recurse -Force "$Root\dist\GalaxyTrackpad" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Root\build\galaxytrackpad" -ErrorAction SilentlyContinue

Write-Host "Running PyInstaller..."
& $Py -m PyInstaller --noconfirm --clean "$Root\packaging\galaxytrackpad.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$Out = Join-Path $Root "dist\GalaxyTrackpad"
if (-not (Test-Path (Join-Path $Out "GalaxyTrackpad.exe"))) {
    throw "Build failed: GalaxyTrackpad.exe not found in $Out"
}

# Sanity: PySide6 must be inside _internal
$pyside = Get-ChildItem -Path (Join-Path $Out "_internal") -Recurse -Filter "Qt6Core.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pyside) {
    throw "Build looks broken: Qt6Core.dll missing under _internal (PySide6 not bundled)."
}
Write-Host "Bundled Qt: $($pyside.FullName)"

$AdbSrc = Join-Path $Root "platform-tools"
$AdbDst = Join-Path $Out "platform-tools"
if (Test-Path (Join-Path $AdbSrc "adb.exe")) {
    Write-Host "Copying platform-tools next to the exe..."
    if (Test-Path $AdbDst) { Remove-Item -Recurse -Force $AdbDst }
    Copy-Item -Recurse $AdbSrc $AdbDst
} else {
    Write-Warning "platform-tools\adb.exe missing — place ADB beside the exe before running."
}

$SettingsSrc = Join-Path $Root "windows\galaxytrackpad_settings.json"
$SettingsDst = Join-Path $Out "galaxytrackpad_settings.json"
if ((Test-Path $SettingsSrc) -and -not (Test-Path $SettingsDst)) {
    Copy-Item $SettingsSrc $SettingsDst
    Write-Host "Copied settings JSON next to the exe."
}

Write-Host ""
Write-Host "OK: $Out\GalaxyTrackpad.exe"
Write-Host "Run that folder's GalaxyTrackpad.exe (keep platform-tools beside it)."
