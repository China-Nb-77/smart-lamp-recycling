param(
    [string]$WorkspaceRoot = "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)"
)

$h5Dir = Join-Path $WorkspaceRoot "AI灯泡"
$apiDir = Join-Path $WorkspaceRoot "wechat_payment_fix\pay-demo"
$rnDir = Join-Path $WorkspaceRoot "AILightShell"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$h5Dir'; & 'D:\抓包\npm.cmd' run dev -- --host 0.0.0.0"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$apiDir'; mvn spring-boot:run"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rnDir'; & 'D:\抓包\npm.cmd' start"

Write-Host "Started H5, backend, and Metro in separate PowerShell windows."
