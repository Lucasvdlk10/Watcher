# LEIA Watcher V3 Dark Program - in-place offline upgrade from 2.0.0
# User scope only; DOES NOT alter Downloads, SQLite schema, rules or Hermes.
[CmdletBinding()]
param([switch]$ForceReinstall)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Atualizacao suportada apenas em Windows 10/11.' }
$Source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Venv = Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher\.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$PythonW = Join-Path $Venv 'Scripts\pythonw.exe'
$Data = Join-Path $env:LOCALAPPDATA 'LEIA\Watcher'
$Backups = Join-Path $Data 'upgrade-backups'
$OldWheel = Join-Path $Source 'rollback-bundle\leia_watcher-2.0.0-py3-none-any.whl'
$Wheel = Join-Path $Source 'dist\leia_watcher-3.0.0-py3-none-any.whl'
$HadCore = $false; $Stopped = $false; $Snapshot = $null
if (!(Test-Path -LiteralPath $Python)) { throw 'Instalacao atual nao encontrada. V3 e um UPDATE de 2.0.0 e nao um produto substituto.' }
if (!(Test-Path -LiteralPath $Wheel)) { throw 'Wheel V3 nao encontrado.' }
if (!(Test-Path -LiteralPath $OldWheel)) { throw 'Wheel V2 de rollback nao encontrado. Nenhuma alteracao feita.' }
if (!(Test-Path -LiteralPath (Join-Path $Data 'config.json'))) { throw 'Configuracao existente ausente; upgrade seguro cancelado.' }
& $Python (Join-Path $Source 'migrations\v2_to_v3.py') $Data
if ($LASTEXITCODE -ne 0) { throw 'Schema/data V2 incompativel; sem alteracoes.' }

Write-Host 'LEIA Watcher V3 - atualizacao REAL do programa instalado' -ForegroundColor Cyan
Write-Host 'Preflight: integridade de artefatos e verificacao de versao...'
& (Join-Path $PSScriptRoot 'verify.ps1')
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Hash de release invalido.' }
$InstalledVersion = (& $Python -c 'import leia_watcher; print(leia_watcher.__version__)' | Select-Object -Last 1).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Falha ao detectar versao instalada.' }
if ($InstalledVersion -ne '2.0.0' -and !($ForceReinstall -and $InstalledVersion -eq '3.0.0')) {
  throw "Versao instalada $InstalledVersion nao suportada (esperada: 2.0.0). Instalacao cancelada."
}
# Fail closed: do not mutate Python modules while an old GUI is executing.
try {
  $GuiProcesses = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains('leia_watcher.ui') -and
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Venv,[StringComparison]::OrdinalIgnoreCase)
  })
} catch { throw 'Nao foi possivel verificar a UI ativa. Por seguranca, instalacao cancelada.' }
if ($GuiProcesses.Count -gt 0) { throw 'Janela LEIA Watcher aberta. Feche a interface antes de instalar. O core sera parado pelo instalador.' }
try {
  & $Python -m leia_watcher.cli ping *> $null
  $HadCore=($LASTEXITCODE -eq 0)
} catch { $HadCore=$false }
if ($HadCore) {
  $BeforeStatus = (& $Python -m leia_watcher.cli status | Out-String | ConvertFrom-Json)
  if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar pendencias antes do upgrade.' }
  if ([int]$BeforeStatus.pending -ne 0) { throw 'Ha operacoes pendentes. Upgrade cancelado para evitar movimentacoes parciais.' }
  Write-Host 'Parando o core por IPC autenticado...'
  & $Python -m leia_watcher.cli stop *> $null
  if ($LASTEXITCODE -ne 0) { throw 'Parada por IPC falhou. Nenhum arquivo alterado.' }
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 200
    $Probe = Start-Process -FilePath $Python -ArgumentList @('-m','leia_watcher.cli','ping') -WindowStyle Hidden -Wait -PassThru
    if ($Probe.ExitCode -ne 0) { $Stopped=$true; break }
  }
  if (!$Stopped) { throw 'Core nao encerrou; atualizacao cancelada.' }
}

New-Item -ItemType Directory -Force -Path $Backups | Out-Null
$Stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')
$Snapshot = Join-Path $Backups ("v3-"+$Stamp)
$UpgradeStarted = $false
try {
  Write-Host 'Criando snapshot consistente SQLite + config...'
  & $Python (Join-Path $PSScriptRoot 'upgrade_helper.py') snapshot $Data $Snapshot
  if ($LASTEXITCODE -ne 0) { throw 'Backup SQLite falhou. Wheel V3 NAO instalado.' }
  Copy-Item -LiteralPath $OldWheel -Destination $Snapshot -ErrorAction Stop
  $UpgradeStarted=$true
  & $Python -m pip install --no-index --no-deps --force-reinstall $Wheel
  if ($LASTEXITCODE -ne 0) { throw 'pip install offline falhou.' }
  # Check installed package, packaged official images, core contract and existing DB.
  & $Python -c 'from leia_watcher import __version__; from leia_watcher import ui,admin,config; from importlib.resources import files; import sqlite3; from pathlib import Path; assert __version__=="3.0.0"; a=files("leia_watcher").joinpath("assets"); assert all(a.joinpath(x).is_file() for x in ("leia_watcher_256.png","nav_overview_idle.png","nav_hermes_active.png","obsidian_wave.png")); c=config.load(); assert c["api"]["host"]=="127.0.0.1"; db=config.home()/"data"/"watcher.db"; conn=sqlite3.connect(str(db)); assert conn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; conn.close(); print("V3_HEALTH_OK")'
  if ($LASTEXITCODE -ne 0) { throw 'Health V3 offline falhou.' }
  if ($HadCore) {
    Start-Process -FilePath $PythonW -ArgumentList '-m leia_watcher.main' -WorkingDirectory (Split-Path $Python)
    $Healthy=$false
    for ($i=0; $i -lt 35; $i++) {
      Start-Sleep -Milliseconds 300
      & $Python -m leia_watcher.cli ping *> $null
      if ($LASTEXITCODE -eq 0) { $Healthy=$true; break }
    }
    if (!$Healthy) { throw 'Core V3 nao respondeu ao IPC. Rollback automatico acionado.' }
    $PostPing=(& $Python -m leia_watcher.cli ping | Out-String | ConvertFrom-Json)
    if ($PostPing.version -ne '3.0.0' -or $PostPing.no_llm -ne $true -or $PostPing.db -ne 'ok') {
      throw 'Core V3 respondeu com versao/seguranca/SQLite inesperados; rollback acionado.'
    }
  }
  # Preserve existing autostart (core); create/update Start Menu link for new UI.
  $Menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'L.E.I.A. Watcher.lnk'
  $WSH = New-Object -ComObject WScript.Shell
  $Shortcut = $WSH.CreateShortcut($Menu)
  $Shortcut.TargetPath=$PythonW
  $Shortcut.Arguments='-m leia_watcher.ui'
  $Shortcut.WorkingDirectory=(Split-Path $Python)
  $Shortcut.Description='LEIA Watcher 3.0 Dark Program - interface local'
  $Shortcut.Save()
  Set-Content -LiteralPath (Join-Path $Backups 'latest-v3.txt') -Value $Snapshot -Encoding UTF8
  Write-Host 'SUCESSO: Watcher 3.0 instalado, dados e organizacao de Downloads preservados.' -ForegroundColor Green
  Write-Host 'Abra scripts\INICIAR_GUI.cmd ou o atalho L.E.I.A. Watcher.'
  Write-Host 'Rollback para V2: scripts\ROLLBACK_UPDATE_VISUAL.cmd'
} catch {
  $Failure=$_.Exception.Message
  Write-Warning "Falha no update: $Failure"
  if ($UpgradeStarted) {
    try {
      & $Python -m leia_watcher.cli stop *> $null
      Start-Sleep -Milliseconds 800
      & $Python -m pip install --no-index --no-deps --force-reinstall $OldWheel
      if ($LASTEXITCODE -ne 0) { throw 'Falha ao reinstalar wheel V2.' }
      Write-Warning 'Rollback automatico do CODIGO executado (V2). Snapshot SQLite preservado.'
    } catch { Write-Warning "ROLLBACK DO CODIGO FALHOU: $($_.Exception.Message) - restaurar manualmente wheel V2 em rollback-bundle." }
  }
  if ($HadCore -and $Stopped) {
    try { Start-Process -FilePath $PythonW -ArgumentList '-m leia_watcher.main' -WorkingDirectory (Split-Path $Python) }
    catch { Write-Warning 'Core nao reiniciado automaticamente; use INICIAR_CORE.cmd' }
  }
  throw "Update abortado: $Failure"
}
