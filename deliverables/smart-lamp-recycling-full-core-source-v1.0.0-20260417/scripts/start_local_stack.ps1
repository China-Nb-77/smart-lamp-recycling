param()

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Mvn = "C:\Users\LEGION\Desktop\灯泡\.tools\apache-maven-3.9.9\bin\mvn.cmd"
$Python = "C:\Users\LEGION\Desktop\灯泡\.venv\Scripts\python.exe"
$Npm = "C:\Program Files\nodejs\npm.cmd"

$env:TAOBAO_BROWSER = "edge"
$env:TAOBAO_HEADLESS = "false"
$env:RECOMMEND_SERVICE_URL = "http://127.0.0.1:8000/api/recommend"

Write-Host "Start services manually with the following commands:"
Write-Host ""
Write-Host "1. Fulfillment:"
Write-Host "   cd `"$Root\services\fulfillment-api`""
Write-Host "   & `"$Mvn`" spring-boot:run"
Write-Host ""
Write-Host "2. Payment:"
Write-Host "   cd `"$Root\services\payment-api`""
Write-Host "   & `"$Mvn`" spring-boot:run ""-Dspring-boot.run.arguments=--server.port=8081 --server.address=127.0.0.1"""
Write-Host ""
Write-Host "3. Vision:"
Write-Host "   cd `"$Root\services\vision-api`""
Write-Host "   & `"$Python`" scripts\vision_local_server.py"
Write-Host ""
Write-Host "4. Frontend:"
Write-Host "   cd `"$Root\frontend`""
Write-Host "   & `"$Npm`" run dev -- --host 0.0.0.0 --port 5173"
