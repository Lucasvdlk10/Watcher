# LEIA Watcher 4 / offline, per-user, frontend-only transaction.
[CmdletBinding()]param([switch]$Quiet)
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
if($env:OS -ne 'Windows_NT'){throw 'Somente Windows.'}
$Root=$PSScriptRoot
$Source=Join-Path $Root 'Publish'
$Binary=Join-Path $Source 'LEIAWatcher.App.exe'
$Dest=Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher.WinUI4'
$Data=Join-Path $env:LOCALAPPDATA 'LEIA\Watcher'
$Venv=Join-Path $env:LOCALAPPDATA 'Programs\LEIAWatcher\.venv\Scripts\python.exe'
$Backups=Join-Path $Data 'upgrade-backups'
$Menu=Join-Path ([Environment]::GetFolderPath('Programs')) 'L.E.I.A. Watcher.lnk'
$Marker=Join-Path $Backups 'latest-v4.json'
if(Test-Path $Marker){throw 'Ja ha um frontend V4 registrado. Execute rollback antes de reinstalar, para manter retorno garantido a V3.'}
if(!(Test-Path $Binary)){throw 'Build Release x64 ausente. Não é permitido instalar um protótipo.'}
if(!(Test-Path (Join-Path $Source 'Bridge\watcher_bridge.py'))){throw 'Ponte IPC ausente. Cancelado.'}
if(!(Test-Path $Venv)){throw 'Instalação existente do LEIA Watcher V3 não encontrada.'}
if(!(Test-Path (Join-Path $Data 'config.json'))){throw 'Configuração V3 ausente. Cancelado.'}
$Version=(& $Venv -c 'import leia_watcher;print(leia_watcher.__version__)' | Select-Object -Last 1).Trim()
if($LASTEXITCODE -ne 0 -or $Version -ne '3.0.0'){throw "Core V3.0.0 exigido; detectado $Version. Nada alterado."}
# Verify file hash list produced on the packaging machine; abort on tampering.
$Checks=Join-Path $Root 'PUBLISH_SHA256SUMS.txt'
if(!(Test-Path $Checks)){throw 'Manifesto SHA256 dos binários não encontrado.'}
foreach($line in Get-Content $Checks){if(!$line.Trim()){continue}; $cols=$line -split '\s+',2; if($cols.Count -ne 2){throw 'Manifesto inválido.'};$rel=$cols[1].Trim().Replace('/', '\');if($rel.StartsWith('..') -or [IO.Path]::IsPathRooted($rel)){throw 'Caminho inválido no manifesto.'};$p=Join-Path $Root $rel;if(!(Test-Path $p)){throw "Ausente $rel"}; if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ine $cols[0]){throw "Hash inválido: $rel"}}
$Running=@(Get-CimInstance Win32_Process -Filter "Name='LEIAWatcher.App.exe'" -ErrorAction Stop | Where-Object {$_.ExecutablePath -and $_.ExecutablePath.StartsWith($Dest,[StringComparison]::OrdinalIgnoreCase)})
if($Running.Count){throw 'Feche LEIA Watcher 4 antes de atualizar a interface.'}
New-Item -ItemType Directory -Force $Backups | Out-Null
$stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff');$Snapshot=Join-Path $Backups "winui4-$stamp";New-Item -ItemType Directory $Snapshot|Out-Null
# SQLite consistent backup is delegated to the unchanged engine, never copied hot.
try {& $Venv -m leia_watcher.cli backup *> (Join-Path $Snapshot 'database-backup-result.txt')} catch {Write-Warning 'Core não ativo para backup IPC; backup offline será tentado abaixo.'}
& $Venv -c 'import sqlite3,sys;from pathlib import Path;src=Path(sys.argv[1]);dst=Path(sys.argv[2]);assert src.exists(); a=sqlite3.connect(str(src));b=sqlite3.connect(str(dst));a.backup(b);assert b.execute("PRAGMA integrity_check").fetchone()[0]=="ok";b.close();a.close()' (Join-Path $Data 'data\watcher.db') (Join-Path $Snapshot 'watcher.db')
if($LASTEXITCODE -ne 0){throw 'Backup consistente do SQLite falhou. Sem alterações de UI.'}
Copy-Item (Join-Path $Data 'config.json') (Join-Path $Snapshot 'config.json') -ErrorAction Stop
$shortcut=$null
if(Test-Path $Menu){$sh=New-Object -ComObject WScript.Shell;$x=$sh.CreateShortcut($Menu);$shortcut=@{TargetPath=$x.TargetPath;Arguments=$x.Arguments;WorkingDirectory=$x.WorkingDirectory;IconLocation=$x.IconLocation;Description=$x.Description}}
$Previous=Join-Path $Snapshot 'previous-frontend'
$Temp="$Dest.next-$stamp"
$Swapped=$false
try {
 if(Test-Path $Temp){Remove-Item $Temp -Recurse -Force}
 New-Item -ItemType Directory -Force $Temp | Out-Null
 Copy-Item -Path (Join-Path $Source '*') -Destination $Temp -Recurse -Force
 if(!(Test-Path (Join-Path $Temp 'LEIAWatcher.App.exe'))){throw 'Arquivos WinUI não foram copiados.'}
 if(Test-Path $Dest){Move-Item -LiteralPath $Dest -Destination $Previous -ErrorAction Stop}
 Move-Item -LiteralPath $Temp -Destination $Dest -ErrorAction Stop;$Swapped=$true
 $WSH=New-Object -ComObject WScript.Shell;$Link=$WSH.CreateShortcut($Menu);$Link.TargetPath=Join-Path $Dest 'LEIAWatcher.App.exe';$Link.Arguments='';$Link.WorkingDirectory=$Dest;$Link.IconLocation=Join-Path $Dest 'LEIAWatcher.App.exe';$Link.Description='LEIA Watcher 4 - WinUI native';$Link.Save()
 # Health: unchanged core, no motor restart and no file operations.
 & $Venv -c 'import sqlite3,sys;from pathlib import Path;from leia_watcher import __version__;assert __version__=="3.0.0";p=Path(sys.argv[1]);c=sqlite3.connect(str(p));assert c.execute("PRAGMA integrity_check").fetchone()[0]=="ok";c.close();print("CORE_DATA_OK")' (Join-Path $Data 'data\watcher.db')
 if($LASTEXITCODE -ne 0){throw 'Verificação core/SQLite falhou. Rollback da UI será acionado.'}
 @{Snapshot=$Snapshot;Menu=$Menu;Shortcut=$shortcut;InstalledAt=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $Marker -Encoding UTF8
 Write-Host 'LEIA Watcher 4 WinUI instalado. Core 3.0.0 e dados preservados.' -ForegroundColor Green
} catch {
 $errorText=$_.Exception.Message
 if($Swapped -and (Test-Path $Dest)){Remove-Item -LiteralPath $Dest -Recurse -Force}
 if(Test-Path $Previous){Move-Item -LiteralPath $Previous -Destination $Dest}
 if($shortcut){$WSH=New-Object -ComObject WScript.Shell;$Link=$WSH.CreateShortcut($Menu);$Link.TargetPath=$shortcut.TargetPath;$Link.Arguments=$shortcut.Arguments;$Link.WorkingDirectory=$shortcut.WorkingDirectory;$Link.IconLocation=$shortcut.IconLocation;$Link.Description=$shortcut.Description;$Link.Save()}
 elseif(Test-Path $Menu){Remove-Item $Menu -Force}
 throw "Update V4 cancelado e interface anterior restaurada: $errorText"
} finally {if(Test-Path $Temp){Remove-Item $Temp -Recurse -Force}}
