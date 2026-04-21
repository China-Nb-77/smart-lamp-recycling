param(
  [string]$FrontHost = "127.0.0.1",
  [int]$FrontPort = 5173,
  [switch]$SkipFrontendBuild,
  [switch]$SkipJavaBuild
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Logs = Join-Path $Root 'logs'
$PidFile = Join-Path $Root 'scripts\pids.json'
New-Item -ItemType Directory -Path $Logs -Force | Out-Null

function Resolve-CommandPath {
  param([string[]]$Candidates)
  foreach ($candidate in $Candidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($command) {
      return $command.Source
    }
  }
  return $null
}

function Start-Proc {
  param(
    [string]$Name,
    [string]$FilePath,
    [string[]]$CmdArgs,
    [string]$WorkDir
  )
  $out = Join-Path $Logs "$Name.out.log"
  $err = Join-Path $Logs "$Name.err.log"
  $proc = Start-Process -FilePath $FilePath -ArgumentList $CmdArgs -WorkingDirectory $WorkDir -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  return [pscustomobject]@{ name = $Name; pid = $proc.Id; out = $out; err = $err }
}

$java = Resolve-CommandPath @('java.exe', 'java')
$python = Resolve-CommandPath @('python.exe', 'python')
$node = Resolve-CommandPath @('node.exe', 'node')
$npm = Resolve-CommandPath @('npm.cmd', 'npm')
$mvn = Resolve-CommandPath @('mvn.cmd', 'mvn')

if (-not $java) { Write-Error 'Java 17+ not found in PATH.' }
if (-not $python) { Write-Error 'Python 3.11+ not found in PATH.' }
if (-not $node) { Write-Error 'Node.js not found in PATH.' }
if (-not $npm) { Write-Error 'npm not found in PATH.' }
if (-not $mvn) { Write-Error 'Maven not found in PATH.' }

if (-not $SkipFrontendBuild) {
  Push-Location (Join-Path $Root 'frontend')
  & $npm 'ci'
  if ($LASTEXITCODE -ne 0) { throw 'Frontend npm ci failed.' }
  & $npm 'run' 'build'
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
  Pop-Location
}

if (-not $SkipJavaBuild) {
  $fulfillmentRoot = Join-Path $Root 'services\fulfillment-api'
  $fulfillmentExample = Join-Path $fulfillmentRoot 'src\main\resources\application.example.properties'
  $fulfillmentConfig = Join-Path $fulfillmentRoot 'src\main\resources\application.properties'
  if ((Test-Path $fulfillmentExample) -and -not (Test-Path $fulfillmentConfig)) {
    Copy-Item -LiteralPath $fulfillmentExample -Destination $fulfillmentConfig
  }

  Push-Location $fulfillmentRoot
  & $mvn '-DskipTests' 'package'
  if ($LASTEXITCODE -ne 0) { throw 'Fulfillment API build failed.' }
  Pop-Location

  Push-Location (Join-Path $Root 'services\payment-api')
  & $mvn '-DskipTests' 'package'
  if ($LASTEXITCODE -ne 0) { throw 'Payment API build failed.' }
  Pop-Location
}

Push-Location (Join-Path $Root 'services\vision-api')
& $python '-m' 'pip' 'install' '-r' 'requirements-runtime.txt'
if ($LASTEXITCODE -ne 0) { throw 'Vision API dependency installation failed.' }
Pop-Location

$env:FRONT_HOST = $FrontHost
$env:FRONT_PORT = [string]$FrontPort
$env:AI_LIGHT_AGENT_MODE = 'mock'

$started = @()
$started += Start-Proc -Name 'fulfillment_8080' -FilePath $java -CmdArgs @('-jar', (Join-Path $Root 'services\fulfillment-api\target\fulfillment-1.0.0.jar'), '--server.port=8080', '--server.address=127.0.0.1') -WorkDir $Root
$started += Start-Proc -Name 'payment_8081' -FilePath $java -CmdArgs @('-jar', (Join-Path $Root 'services\payment-api\target\pay-demo-patch-0.0.1-SNAPSHOT.jar'), '--server.port=8081', '--server.address=127.0.0.1') -WorkDir $Root
$started += Start-Proc -Name 'vision_8000' -FilePath $python -CmdArgs @((Join-Path $Root 'services\vision-api\scripts\vision_local_server.py')) -WorkDir (Join-Path $Root 'services\vision-api')
$started += Start-Proc -Name 'frontend_5173' -FilePath $python -CmdArgs @((Join-Path $Root 'scripts\frontend_gateway.py')) -WorkDir $Root

$started | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

Start-Sleep -Seconds 3

Write-Host ''
Write-Host 'Started successfully:'
$started | ForEach-Object { Write-Host ("- {0} pid={1}" -f $_.name, $_.pid) }
Write-Host ''
Write-Host "Frontend URL: http://$FrontHost`:$FrontPort"
