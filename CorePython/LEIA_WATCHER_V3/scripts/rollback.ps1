# Rollback V3 -> V2. Does not roll back user data by default.
[CmdletBinding()]
param([switch]$RestoreSnapshot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Windows requerido.' }
$Venv=Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher\.venv'
$Python=Join-Path $Venv 'Scripts\python.exe'
$PythonW=Join-Path $Venv 'Scripts\pythonw.exe'
$Data=Join-Path $env:LOCALAPPDATA 'LEIA\Watcher'
$Latest=Join-Path $Data 'upgrade-backups\latest-v3.txt'
if (!(Test-Path $Python) -or !(Test-Path $Latest)) { throw 'Instalacao/snapshot de V3 indisponivel.' }
$Snapshot=(Get-Content $Latest -Raw).Trim()
$Wheel=Join-Path $Snapshot 'leia_watcher-2.0.0-py3-none-any.whl'
if (!(Test-Path $Wheel)) { throw 'Wheel V2 original ausente. Rollback cancelado.' }
Write-Host 'Rollback LEIA Watcher V3 -> V2' -ForegroundColor Yellow
Write-Host 'Por padrao, regras, arquivos organizados, tokens, SQLite atual e historico sao PRESERVADOS.'
$Confirmation= if ($RestoreSnapshot) { 'RESTAURAR-DADOS' } else { 'RESTAURAR' }
$Typed=Read-Host "Digite $Confirmation para confirmar"
if ($Typed -cne $Confirmation) { throw 'Rollback cancelado.' }
$Gui=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('leia_watcher.ui') -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Venv,[StringComparison]::OrdinalIgnoreCase) })
if ($Gui.Count -gt 0) { throw 'Feche a interface LEIA Watcher antes de voltar para V2.' }
$HadCore=$false
try { & $Python -m leia_watcher.cli ping *> $null; $HadCore=($LASTEXITCODE -eq 0) } catch { }
if ($HadCore) {
  & $Python -m leia_watcher.cli stop *> $null
  if ($LASTEXITCODE -ne 0) { throw 'Falha ao parar core por IPC.' }
  $Gone=$false
  for($i=0;$i -lt 60;$i++) { Start-Sleep -Milliseconds 200; & $Python -m leia_watcher.cli ping *> $null; if ($LASTEXITCODE -ne 0) {$Gone=$true;break} }
  if (!$Gone) { throw 'Core permanece ativo; rollback cancelado.' }
}
& $Python -m pip install --no-index --no-deps --force-reinstall $Wheel
if ($LASTEXITCODE -ne 0) { throw 'Instalacao do wheel V2 falhou.' }
if ($RestoreSnapshot) {
  & $Python (Join-Path $PSScriptRoot 'upgrade_helper.py') restore $Data $Snapshot
  if ($LASTEXITCODE -ne 0) { throw 'Falha na restauracao do snapshot de dados.' }
}
& $Python -c 'from leia_watcher import __version__; assert __version__=="2.0.0"; print("V2_RESTORED")'
if ($LASTEXITCODE -ne 0) { throw 'Versao restaurada nao valida.' }
if ($HadCore) { Start-Process -FilePath $PythonW -ArgumentList '-m leia_watcher.main' -WorkingDirectory (Split-Path $Python) }
Write-Host 'Rollback do codigo V2 concluido. Core restabelecido conforme estado anterior.' -ForegroundColor Green
