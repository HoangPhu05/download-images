$ErrorActionPreference = "Stop"

$venvPip = Join-Path $PSScriptRoot ".." "venv" "Scripts" "pip.exe"
if (Test-Path $venvPip) {
  & $venvPip install --upgrade yt-dlp
} else {
  python -m pip install --upgrade yt-dlp
}
