$projectRoot = Split-Path -Parent $PSScriptRoot
$wrapperFile = Join-Path $projectRoot "android\gradle\wrapper\gradle-wrapper.properties"
$zipPath = Join-Path $projectRoot "android\gradle-9.0.0-bin.zip"

if (-not (Test-Path $zipPath)) {
    throw "Missing local Gradle zip: $zipPath"
}

$zipUri = "file:///" + ($zipPath -replace "\\", "/")
$content = Get-Content $wrapperFile -Raw
$updated = [regex]::Replace(
    $content,
    "distributionUrl=.*",
    "distributionUrl=$zipUri"
)

Set-Content -Path $wrapperFile -Value $updated -Encoding UTF8
Write-Host "Updated gradle-wrapper.properties to use local zip:"
Write-Host $zipUri
