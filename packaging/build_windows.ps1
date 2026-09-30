# Build Galaxy Trackpad Windows onedir (Phase 4B)
# Usage (from repo root, conda env galaxytrackpad):
#   powershell -File packaging\build_windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Repo: $Root"
Write-Host "Installing PyInstaller if needed..."
python -m pip install -q "pyinstaller>=6.3,<7"

Write-Host "Cleaning previous dist/build..."
Remove-Item -Recurse -Force "$Root\dist\GalaxyTrackpad" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Root\build\galaxytrackpad" -ErrorAction SilentlyContinue

Write-Host "Running PyInstaller..."
python -m PyInstaller --noconfirm --clean "$Root\packaging\galaxytrackpad.spec"

$Out = Join-Path $Root "dist\GalaxyTrackpad"
if (-not (Test-Path (Join-Path $Out "GalaxyTrackpad.exe"))) {
    throw "Build failed: GalaxyTrackpad.exe not found in $Out"
}

$AdbSrc = Join-Path $Root "platform-tools"
$AdbDst = Join-Path $Out "platform-tools"
if (Test-Path (Join-Path $AdbSrc "adb.exe")) {
    Write-Host "Copying platform-tools next to the exe..."
    if (Test-Path $AdbDst) { Remove-Item -Recurse -Force $AdbDst }
    Copy-Item -Recurse $AdbSrc $AdbDst
} else {
    Write-Warning "platform-tools\adb.exe missing — place ADB beside the exe before running."
}

# Carry over existing settings if present (dev windows/ JSON).
$SettingsSrc = Join-Path $Root "windows\galaxytrackpad_settings.json"
$SettingsDst = Join-Path $Out "galaxytrackpad_settings.json"
if ((Test-Path $SettingsSrc) -and -not (Test-Path $SettingsDst)) {
    Copy-Item $SettingsSrc $SettingsDst
    Write-Host "Copied settings JSON next to the exe."
}

Write-Host ""
Write-Host "OK: $Out\GalaxyTrackpad.exe"
Write-Host "Run that folder's GalaxyTrackpad.exe (keep platform-tools beside it)."
