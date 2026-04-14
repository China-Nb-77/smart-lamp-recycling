param(
    [Parameter(Mandatory = $true)]
    [string]$LanIp
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot "src\config\env.ts"
$content = Get-Content $envFile -Raw
$content = [regex]::Replace($content, "http://[0-9\.]+:5173", "http://$LanIp`:5173")
$content = [regex]::Replace($content, "http://[0-9\.]+:8080", "http://$LanIp`:8080")
Set-Content -Path $envFile -Value $content -Encoding UTF8
Write-Host "Updated env.ts with LAN IP $LanIp"
