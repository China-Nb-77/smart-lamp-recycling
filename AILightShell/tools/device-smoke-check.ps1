param(
    [string]$LanIp = "192.168.132.109",
    [int]$H5Port = 5173,
    [int]$ApiPort = 8080,
    [string]$SampleImagePath = ""
)

$ErrorActionPreference = "Stop"

function Test-Port {
    param(
        [string]$HostName,
        [int]$Port
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $wait = $async.AsyncWaitHandle.WaitOne(3000, $false)
        if (-not $wait) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Invoke-SimpleGet {
    param([string]$Url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Upload-Image {
    param(
        [string]$ApiBaseUrl,
        [string]$ImagePath
    )

    Add-Type -AssemblyName System.Net.Http
    $client = New-Object System.Net.Http.HttpClient
    $multipart = New-Object System.Net.Http.MultipartFormDataContent
    $stream = [System.IO.File]::OpenRead($ImagePath)
    $streamContent = New-Object System.Net.Http.StreamContent($stream)
    $streamContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("image/jpeg")
    $multipart.Add($streamContent, "file", [System.IO.Path]::GetFileName($ImagePath))
    try {
        $response = $client.PostAsync("$ApiBaseUrl/api/v1/files/upload", $multipart).Result
        $body = $response.Content.ReadAsStringAsync().Result
        return @{
            status = [int]$response.StatusCode
            body = $body
        }
    } finally {
        $stream.Dispose()
        $multipart.Dispose()
        $client.Dispose()
    }
}

$apiBaseUrl = "http://$LanIp`:$ApiPort"
$h5BaseUrl = "http://$LanIp`:$H5Port"

Write-Host "Check LAN IP: $LanIp"
Write-Host "H5 URL: $h5BaseUrl"
Write-Host "API URL: $apiBaseUrl"

$h5PortReady = Test-Port -HostName $LanIp -Port $H5Port
$apiPortReady = Test-Port -HostName $LanIp -Port $ApiPort

Write-Host "H5 port ready: $h5PortReady"
Write-Host "API port ready: $apiPortReady"

$h5HttpReady = Invoke-SimpleGet -Url $h5BaseUrl
$apiHttpReady = Invoke-SimpleGet -Url "$apiBaseUrl/order-view?order_id=test&token=test"

Write-Host "H5 HTTP reachable: $h5HttpReady"
Write-Host "API HTTP reachable: $apiHttpReady"

if ($SampleImagePath -and (Test-Path $SampleImagePath)) {
    Write-Host "Upload smoke test: $SampleImagePath"
    $uploadResult = Upload-Image -ApiBaseUrl $apiBaseUrl -ImagePath $SampleImagePath
    Write-Host "Upload status: $($uploadResult.status)"
    Write-Host "Upload body: $($uploadResult.body)"
} else {
    Write-Host "Upload smoke test skipped. Pass -SampleImagePath to enable."
}

try {
    $adbPath = (Get-Command adb -ErrorAction Stop).Source
    Write-Host "adb found: $adbPath"
    & $adbPath devices
} catch {
    Write-Host "adb not found in PATH. Real device install must be checked manually."
}
