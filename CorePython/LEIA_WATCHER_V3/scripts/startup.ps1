param([switch]$Enable,[switch]$Disable)
$ErrorActionPreference = 'Stop'
$Startup = [Environment]::GetFolderPath('Startup')
$Link = Join-Path $Startup 'L.E.I.A. Watcher.lnk'
if ($Enable) {
  $Py = Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher\.venv\Scripts\pythonw.exe'
  if (!(Test-Path $Py)) { throw 'Execute instalador primeiro.' }
  $wsh = New-Object -ComObject WScript.Shell
  $shortcut = $wsh.CreateShortcut($Link)
  $shortcut.TargetPath = $Py
  $shortcut.Arguments = '-m leia_watcher.main'
  $shortcut.WorkingDirectory = Split-Path $Py
  $shortcut.Description = 'LEIA Watcher local core (sem privilegios elevados)'
  $shortcut.Save()
  Write-Host 'Inicializacao no logon ativada somente para este usuario.'
} elseif ($Disable) {
  if (Test-Path $Link) { Remove-Item -LiteralPath $Link }
  Write-Host 'Inicializacao no logon desativada.'
} else { throw 'Informe -Enable ou -Disable' }
