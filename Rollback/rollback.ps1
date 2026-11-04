# Restore prior GUI only; preserve current SQLite, config, tokens and post-update events.
[CmdletBinding()]param([switch]$RestoreDatabaseSnapshot)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
if($RestoreDatabaseSnapshot){throw 'Restauracao de banco exige procedimento offline manual; rollback do frontend nao modifica SQLite.'}
$Data=Join-Path $env:LOCALAPPDATA 'LEIA\Watcher'
$Dest=Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher.WinUI4'
$Marker=Join-Path $Data 'upgrade-backups\latest-v4.json'
if(!(Test-Path $Marker)){throw 'Metadata de instalação V4 inexistente; nenhuma alteração.'}
$m=Get-Content $Marker -Raw|ConvertFrom-Json
$Snapshot=$m.Snapshot
if(!(Test-Path $Snapshot)){throw 'Backup V4 não encontrado.'}
$Running=@(Get-CimInstance Win32_Process -Filter "Name='LEIAWatcher.App.exe'" | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($Dest,[StringComparison]::OrdinalIgnoreCase)})
if($Running.Count){throw 'Feche a janela WinUI antes do rollback.'}
$Confirmation=if($RestoreDatabaseSnapshot){'RESTAURAR-DADOS'}else{'VOLTAR-V3'}
$typed=Read-Host "Confirme digitando $Confirmation"
if($typed -cne $Confirmation){throw 'Rollback cancelado.'}
$Previous=Join-Path $Snapshot 'previous-frontend'
if(Test-Path $Dest){Remove-Item -LiteralPath $Dest -Recurse -Force}
if(Test-Path $Previous){Move-Item -LiteralPath $Previous -Destination $Dest}
$Menu=$m.Menu
if($m.Shortcut){$WSH=New-Object -ComObject WScript.Shell;$x=$WSH.CreateShortcut($Menu);$x.TargetPath=$m.Shortcut.TargetPath;$x.Arguments=$m.Shortcut.Arguments;$x.WorkingDirectory=$m.Shortcut.WorkingDirectory;$x.Description=$m.Shortcut.Description;$x.IconLocation=$m.Shortcut.IconLocation;$x.Save()}
elseif(Test-Path $Menu){Remove-Item $Menu -Force}
Write-Host 'Rollback visual realizado. Core V3, banco e histórico atual permaneceram intactos.' -ForegroundColor Green
