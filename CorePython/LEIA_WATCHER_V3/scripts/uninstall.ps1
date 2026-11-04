$ErrorActionPreference = 'Stop'
$Base = Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher'
$Py = Join-Path $Base '.venv\Scripts\python.exe'
if (Test-Path $Py) { & $Py -m leia_watcher.cli stop 2>$null }
& (Join-Path $PSScriptRoot 'startup.ps1') -Disable
Start-Sleep -Seconds 1
if (Test-Path $Base) { Remove-Item -LiteralPath $Base -Force -Recurse }
Write-Host 'Aplicacao desinstalada. SQLite/config/logs/backups preservados por padrao.'
Write-Host "Dados: $env:LOCALAPPDATA\LEIA\Watcher"
Write-Host 'Nao exclua dados ou backups sem revisar a recuperacao e historico.'
