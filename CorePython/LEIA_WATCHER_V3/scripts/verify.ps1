$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$List = Join-Path $Root 'SHA256_MANIFEST.txt'
if (!(Test-Path $List)) { throw 'Manifesto SHA256 ausente.' }
$bad = 0
Get-Content $List | ForEach-Object {
  if ($_ -match '^([a-fA-F0-9]{64})\s{2}(.+)$') {
    $want = $matches[1].ToUpperInvariant()
    $relative = $matches[2]
    $full = Join-Path $Root $relative
    if (!(Test-Path $full) -or (Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash -ne $want) {
      Write-Host "INCORRETO: $relative" -ForegroundColor Red
      $bad++
    }
  }
}
if ($bad -gt 0) { throw "$bad arquivo(s) falharam na verificacao." }
Write-Host 'Todos os arquivos do manifesto possuem hash correto.' -ForegroundColor Green
