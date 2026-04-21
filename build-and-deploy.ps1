$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerIP = if ($env:SERVER_IP) { $env:SERVER_IP } else { "114.215.177.52" }
$ServerUser = if ($env:SERVER_USER) { $env:SERVER_USER } else { "root" }
$ServerSshPort = if ($env:SERVER_SSH_PORT) { $env:SERVER_SSH_PORT } else { "22" }
$ServerPath = if ($env:SERVER_PATH) { $env:SERVER_PATH } else { "/var/www/html" }
$RemoteAppDir = if ($env:REMOTE_APP_DIR) { $env:REMOTE_APP_DIR } else { "/opt/smart-lamp-assistant" }
$PublicBaseUrl = if ($env:PUBLIC_BASE_URL) { $env:PUBLIC_BASE_URL } else { "http://$ServerIP" }
$SessionSecret = if ($env:SESSION_SECRET) { $env:SESSION_SECRET } else { "change-me-before-production" }
$WorkflowMode = if ($env:WORKFLOW_MODE) { $env:WORKFLOW_MODE } else { "mock" }
$PaymentMode = if ($env:PAYMENT_MODE) { $env:PAYMENT_MODE } else { "mock" }

if ([string]::IsNullOrWhiteSpace($ServerIP)) {
  throw "Set SERVER_IP first, for example: set SERVER_IP=47.100.10.20"
}

function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing command: $Name"
  }
}

Require-Command npm
Require-Command ssh
Require-Command scp
Require-Command tar

Set-Location $RootDir

Write-Host "==> Install root dependencies"
& npm install

Write-Host "==> Install frontend dependencies"
& npm --prefix frontend install

Write-Host "==> Build frontend for $PublicBaseUrl"
$env:VITE_API_BASE_URL = $PublicBaseUrl
$env:VITE_VISION_API_BASE_URL = $PublicBaseUrl
$env:VITE_PAYMENT_API_BASE_URL = $PublicBaseUrl
& npm --prefix frontend run build
Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:VITE_VISION_API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:VITE_PAYMENT_API_BASE_URL -ErrorAction SilentlyContinue

if (-not (Test-Path "$RootDir\android")) {
  Write-Host "==> Add Android platform"
  & npx cap add android
}

Write-Host "==> Sync Capacitor Android project"
& npx cap sync android

$ManifestPath = Join-Path $RootDir "android\app\src\main\AndroidManifest.xml"
if ((Test-Path $ManifestPath) -and $PublicBaseUrl.StartsWith("http://")) {
  Write-Host "==> Enable cleartext HTTP for Android"
  $manifestText = Get-Content -Raw $ManifestPath
  if ($manifestText -notmatch "usesCleartextTraffic") {
    $manifestText = $manifestText -replace "<application", '<application android:usesCleartextTraffic="true"'
    Set-Content -Path $ManifestPath -Value $manifestText -Encoding UTF8
  }
}

Write-Host "==> Build Android debug APK"
Push-Location (Join-Path $RootDir "android")
try {
  & .\gradlew.bat assembleDebug
} finally {
  Pop-Location
}

$DeliveryDir = Join-Path $RootDir "delivery"
New-Item -ItemType Directory -Force -Path $DeliveryDir | Out-Null
Copy-Item `
  -Force `
  -Path (Join-Path $RootDir "android\app\build\outputs\apk\debug\app-debug.apk") `
  -Destination (Join-Path $DeliveryDir "SmartLampAssistant.apk")

$DeployTmp = Join-Path $RootDir ".deploy-package"
if (Test-Path $DeployTmp) {
  Remove-Item -Recurse -Force $DeployTmp
}
New-Item -ItemType Directory -Force -Path $DeployTmp | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DeployTmp "data") | Out-Null

Write-Host "==> Prepare backend bundle"
Copy-Item -Force (Join-Path $RootDir "Dockerfile") $DeployTmp
Copy-Item -Force (Join-Path $RootDir "pyproject.toml") $DeployTmp
Copy-Item -Force (Join-Path $RootDir "README.md") $DeployTmp
Copy-Item -Recurse -Force (Join-Path $RootDir "backend") $DeployTmp
Copy-Item -Recurse -Force (Join-Path $RootDir "image_quote_system") $DeployTmp
Copy-Item -Recurse -Force (Join-Path $RootDir "configs") $DeployTmp
Copy-Item -Recurse -Force (Join-Path $RootDir "data\catalog") (Join-Path $DeployTmp "data")
if (Test-Path (Join-Path $RootDir "images")) {
  Copy-Item -Recurse -Force (Join-Path $RootDir "images") $DeployTmp
}

$ComposeText = @"
services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ai_light
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      - redis
      - postgres
    ports:
      - "127.0.0.1:8000:8000"

volumes:
  postgres_data:
"@
Set-Content -Path (Join-Path $DeployTmp "docker-compose.yml") -Value $ComposeText -Encoding UTF8

$NginxText = @"
server {
    listen 80 default_server;
    server_name _;

    root $ServerPath;
    index download.html;
    client_max_body_size 12m;

    location = / {
        try_files /download.html =404;
    }

    location = /download.html {
        try_files `$uri =404;
    }

    location = /SmartLampAssistant.apk {
        default_type application/vnd.android.package-archive;
        add_header Content-Disposition 'attachment; filename="SmartLampAssistant.apk"';
        try_files `$uri =404;
    }

    location = /health { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /preflight { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /quote { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /quote-upload { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /recommend { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /classify { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /classify-upload { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /classify-lamp { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /classify-lamp-upload { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }
    location = /catalog-image { proxy_pass http://127.0.0.1:8000; include /etc/nginx/proxy_params; }

    location /agent/ {
        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
    }
}
"@
Set-Content -Path (Join-Path $DeployTmp "nginx.smart-lamp-assistant.conf") -Value $NginxText -Encoding UTF8

$EnvText = @"
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/ai_light
AI_LIGHT_SESSION_SECRET=$SessionSecret
AI_LIGHT_WORKFLOW_MODE=$WorkflowMode
AI_LIGHT_PAYMENT_MODE=$PaymentMode
AI_LIGHT_ALLOW_REVIEW_FALLBACK=true
AI_LIGHT_BASE_DIR=/app
AI_LIGHT_CONFIG_DIR=/app/configs
AI_LIGHT_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,capacitor://localhost,ionic://localhost,$PublicBaseUrl
"@
Set-Content -Path (Join-Path $DeployTmp ".env") -Value $EnvText -Encoding UTF8

$BackendTar = Join-Path $DeliveryDir "smart-lamp-backend.tar.gz"
if (Test-Path $BackendTar) {
  Remove-Item -Force $BackendTar
}

Write-Host "==> Pack backend bundle"
& tar -czf $BackendTar -C $DeployTmp .

Write-Host "==> Upload APK, download page and backend bundle"
& scp -P $ServerSshPort (Join-Path $DeliveryDir "SmartLampAssistant.apk") "${ServerUser}@${ServerIP}:${ServerPath}/SmartLampAssistant.apk"
& scp -P $ServerSshPort (Join-Path $RootDir "download.html") "${ServerUser}@${ServerIP}:${ServerPath}/download.html"
& scp -P $ServerSshPort $BackendTar "${ServerUser}@${ServerIP}:/tmp/smart-lamp-backend.tar.gz"
& scp -P $ServerSshPort (Join-Path $DeployTmp "nginx.smart-lamp-assistant.conf") "${ServerUser}@${ServerIP}:/tmp/nginx.smart-lamp-assistant.conf"

Write-Host "==> Deploy backend and Nginx on server"
$RemoteScript = @"
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-plugin nginx
systemctl enable docker
systemctl start docker
systemctl enable nginx
mkdir -p "$RemoteAppDir"
tar -xzf /tmp/smart-lamp-backend.tar.gz -C "$RemoteAppDir"
cp /tmp/nginx.smart-lamp-assistant.conf /etc/nginx/sites-available/smart-lamp-assistant.conf
ln -sf /etc/nginx/sites-available/smart-lamp-assistant.conf /etc/nginx/sites-enabled/smart-lamp-assistant.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
cd "$RemoteAppDir"
docker compose up -d --build
"@

$RemoteScript | & ssh -p $ServerSshPort "${ServerUser}@${ServerIP}" "bash -s"

Write-Host "Done."
Write-Host "APK: $PublicBaseUrl/SmartLampAssistant.apk"
Write-Host "Download page: $PublicBaseUrl/download.html"
Write-Host "Health: $PublicBaseUrl/health"
