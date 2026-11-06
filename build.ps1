# Baut dist\Paschen.exe (Tests laufen vorher, bei Fehlern wird abgebrochen).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Kein .venv gefunden. Erst: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt" }

& $py tools\icons_bauen.py
if ($LASTEXITCODE -ne 0) { throw "Icons konnten nicht gebaut werden." }

& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests fehlgeschlagen - Build abgebrochen." }

& $py -m PyInstaller --noconfirm --clean --onefile --windowed --name Paschen --add-data "ui;ui" start_paschen.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen." }

$exe = Join-Path $PSScriptRoot "dist\Paschen.exe"
"Fertig: $exe ({0:N1} MB)" -f ((Get-Item $exe).Length / 1MB)
