param()
$ErrorActionPreference = 'Continue'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PidFile = Join-Path $Root 'scripts\pids.json'

if (Test-Path $PidFile) {
  $items = Get-Content $PidFile -Raw | ConvertFrom-Json
  foreach ($item in $items) {
    if ($item.pid) {
      Stop-Process -Id $item.pid -Force -ErrorAction SilentlyContinue
      Write-Host ("Stopped {0} pid={1}" -f $item.name, $item.pid)
    }
  }
  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
} else {
  Write-Host 'No pid file found. Trying best-effort stop by ports...'
}

$ports = 5173, 8000, 8080, 8081
foreach ($p in $ports) {
  $conn = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
  foreach ($c in $conn) {
    Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
  }
}

Write-Host 'Stop completed.'
