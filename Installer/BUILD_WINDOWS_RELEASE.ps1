# Execute on Windows 11 x64 with .NET 10 SDK and cached WinAppSDK NuGet packages.
[CmdletBinding()]param([switch]$Offline)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Dist=Join-Path $Root 'Dist';$Publish=Join-Path $PSScriptRoot 'Publish'
if(!(Get-Command dotnet -ErrorAction SilentlyContinue)){throw 'Instale .NET 10 SDK e Visual Studio 2022 17.12+ com Windows App SDK.'}
New-Item -ItemType Directory -Force $Dist | Out-Null
$RestoreFlag=if($Offline){'--no-restore'}else{''}
Push-Location $Root
try{
 if(!$Offline){& dotnet restore (Join-Path $Root 'LEIAWatcher.sln') -p:Platform=x64 -r win-x64;if($LASTEXITCODE){throw 'NuGet restore falhou'}}
 if(!$Offline){& dotnet restore (Join-Path $Root 'tests\LEIAWatcher.UnitTests\LEIAWatcher.UnitTests.csproj');if($LASTEXITCODE){throw 'Restore unit tests falhou'}}
 & dotnet test (Join-Path $Root 'tests\LEIAWatcher.UnitTests\LEIAWatcher.UnitTests.csproj') -c Release --no-restore
 if($LASTEXITCODE){throw 'Testes .NET falharam; Release bloqueado.'}
 & dotnet publish (Join-Path $Root 'src\LEIAWatcher.App\LEIAWatcher.App.csproj') -c Release -r win-x64 --self-contained true -p:Platform=x64 -p:WindowsAppSDKSelfContained=true -o $Publish --no-restore
 if($LASTEXITCODE){throw 'Build WinUI falhou. Nenhum instalador será emitido.'}
 if(!(Test-Path (Join-Path $Publish 'LEIAWatcher.App.exe'))){throw 'EXE WinUI ausente.'}
 $SetupPath=Join-Path $Root 'Installer\LEIAWatcher.Setup\LEIAWatcher.Setup.csproj'
 if(!$Offline){& dotnet restore $SetupPath -r win-x64;if($LASTEXITCODE){throw 'Restore setup falhou'}}
 & dotnet publish $SetupPath -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o (Join-Path $Dist 'setup-build') --no-restore
 if($LASTEXITCODE){throw 'Build Setup.exe falhou.'}
 $Release=Join-Path $Dist 'LEIA-Watcher-4.0-OFFLINE';New-Item -ItemType Directory -Force $Release|Out-Null
 Copy-Item -Path $Publish -Destination $Release -Recurse -Force
 Copy-Item (Join-Path $PSScriptRoot 'install.ps1') $Release
 Copy-Item (Join-Path $Root 'Rollback\rollback.ps1') (Join-Path $Release 'rollback.ps1')
 Copy-Item (Join-Path $Root 'Rollback\ROLLBACK_LEIA_WATCHER_4.cmd') (Join-Path $Release 'ROLLBACK_LEIA_WATCHER_4.cmd')
 $exe=Get-ChildItem (Join-Path $Dist 'setup-build') -Filter 'LEIAWatcher.Setup.exe'|Select-Object -First 1
 if(!$exe){throw 'Bootstrap EXE ausente'}
 Copy-Item $exe.FullName (Join-Path $Release 'LEIA-Watcher-4.0-Setup.exe')
 $manifest=Join-Path $Release 'PUBLISH_SHA256SUMS.txt'
 $lines=Get-ChildItem (Join-Path $Release 'Publish') -Recurse -File|Sort-Object FullName|ForEach-Object{ $sha=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant();$relative=$_.FullName.Substring($Release.Length+1).Replace('\','/');"$sha $relative" }
 $lines|Set-Content -LiteralPath $manifest -Encoding ascii
 Write-Host "Publicação Windows criada em $Release" -ForegroundColor Green
 Write-Warning 'Execute instalação e rollback em VM Windows antes de promover para produção.'
}finally{Pop-Location}
