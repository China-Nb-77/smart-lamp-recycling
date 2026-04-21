#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_IP="${SERVER_IP:-114.215.177.52}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_SSH_PORT="${SERVER_SSH_PORT:-22}"
SERVER_PATH="${SERVER_PATH:-/var/www/html}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/opt/smart-lamp-assistant}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://${SERVER_IP}}"
SESSION_SECRET="${SESSION_SECRET:-change-me-before-production}"
WORKFLOW_MODE="${WORKFLOW_MODE:-mock}"
PAYMENT_MODE="${PAYMENT_MODE:-mock}"

if [[ -z "$SERVER_IP" ]]; then
  echo "Set SERVER_IP first, for example: SERVER_IP=47.100.10.20 ./build-and-deploy.sh"
  exit 1
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1"
    exit 1
  fi
}

require_command npm
require_command ssh
require_command scp
require_command tar
require_command python

cd "$ROOT_DIR"

echo "==> Install root dependencies"
npm install

echo "==> Install frontend dependencies"
npm --prefix frontend install

echo "==> Build frontend for ${PUBLIC_BASE_URL}"
VITE_API_BASE_URL="$PUBLIC_BASE_URL" \
VITE_VISION_API_BASE_URL="$PUBLIC_BASE_URL" \
VITE_PAYMENT_API_BASE_URL="$PUBLIC_BASE_URL" \
npm --prefix frontend run build

if [[ ! -d "$ROOT_DIR/android" ]]; then
  echo "==> Add Android platform"
  npx cap add android
fi

echo "==> Sync Capacitor Android project"
npx cap sync android

MANIFEST_PATH="$ROOT_DIR/android/app/src/main/AndroidManifest.xml"
if [[ -f "$MANIFEST_PATH" && "$PUBLIC_BASE_URL" == http://* ]]; then
  echo "==> Enable cleartext HTTP for Android"
  python - "$MANIFEST_PATH" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
if "android:usesCleartextTraffic=" not in text:
    text = text.replace("<application", '<application android:usesCleartextTraffic="true"', 1)
    path.write_text(text, encoding="utf-8")
PY
fi

echo "==> Build Android debug APK"
(
  cd "$ROOT_DIR/android"
  chmod +x ./gradlew
  ./gradlew assembleDebug
)

mkdir -p "$ROOT_DIR/delivery"
cp "$ROOT_DIR/android/app/build/outputs/apk/debug/app-debug.apk" \
  "$ROOT_DIR/delivery/SmartLampAssistant.apk"

DEPLOY_TMP="$ROOT_DIR/.deploy-package"
rm -rf "$DEPLOY_TMP"
mkdir -p "$DEPLOY_TMP/data"

echo "==> Prepare backend bundle"
cp "$ROOT_DIR/Dockerfile" "$DEPLOY_TMP/"
cp "$ROOT_DIR/pyproject.toml" "$ROOT_DIR/README.md" "$DEPLOY_TMP/"
cp -R "$ROOT_DIR/backend" "$DEPLOY_TMP/"
cp -R "$ROOT_DIR/image_quote_system" "$DEPLOY_TMP/"
cp -R "$ROOT_DIR/configs" "$DEPLOY_TMP/"
cp -R "$ROOT_DIR/data/catalog" "$DEPLOY_TMP/data/"
if [[ -d "$ROOT_DIR/images" ]]; then
  cp -R "$ROOT_DIR/images" "$DEPLOY_TMP/"
fi

cat > "$DEPLOY_TMP/docker-compose.yml" <<'EOF'
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
EOF

cat > "$DEPLOY_TMP/nginx.smart-lamp-assistant.conf" <<EOF
server {
    listen 80 default_server;
    server_name _;

    root ${SERVER_PATH};
    index download.html;
    client_max_body_size 12m;

    location = / {
        try_files /download.html =404;
    }

    location = /download.html {
        try_files \$uri =404;
    }

    location = /SmartLampAssistant.apk {
        default_type application/vnd.android.package-archive;
        add_header Content-Disposition 'attachment; filename="SmartLampAssistant.apk"';
        try_files \$uri =404;
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
EOF

cat > "$DEPLOY_TMP/.env" <<EOF
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/ai_light
AI_LIGHT_SESSION_SECRET=${SESSION_SECRET}
AI_LIGHT_WORKFLOW_MODE=${WORKFLOW_MODE}
AI_LIGHT_PAYMENT_MODE=${PAYMENT_MODE}
AI_LIGHT_ALLOW_REVIEW_FALLBACK=true
AI_LIGHT_BASE_DIR=/app
AI_LIGHT_CONFIG_DIR=/app/configs
AI_LIGHT_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,capacitor://localhost,ionic://localhost,${PUBLIC_BASE_URL}
EOF

echo "==> Pack backend bundle"
tar -C "$DEPLOY_TMP" -czf "$ROOT_DIR/delivery/smart-lamp-backend.tar.gz" .

echo "==> Upload APK, download page and backend bundle"
scp -P "$SERVER_SSH_PORT" "$ROOT_DIR/delivery/SmartLampAssistant.apk" "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/SmartLampAssistant.apk"
scp -P "$SERVER_SSH_PORT" "$ROOT_DIR/download.html" "${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/download.html"
scp -P "$SERVER_SSH_PORT" "$ROOT_DIR/delivery/smart-lamp-backend.tar.gz" "${SERVER_USER}@${SERVER_IP}:/tmp/smart-lamp-backend.tar.gz"
scp -P "$SERVER_SSH_PORT" "$DEPLOY_TMP/nginx.smart-lamp-assistant.conf" "${SERVER_USER}@${SERVER_IP}:/tmp/nginx.smart-lamp-assistant.conf"

echo "==> Deploy backend and Nginx on server"
ssh -p "$SERVER_SSH_PORT" "${SERVER_USER}@${SERVER_IP}" bash <<EOF
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-plugin nginx
systemctl enable docker
systemctl start docker
systemctl enable nginx

mkdir -p "${REMOTE_APP_DIR}"
tar -xzf /tmp/smart-lamp-backend.tar.gz -C "${REMOTE_APP_DIR}"

cp /tmp/nginx.smart-lamp-assistant.conf /etc/nginx/sites-available/smart-lamp-assistant.conf
ln -sf /etc/nginx/sites-available/smart-lamp-assistant.conf /etc/nginx/sites-enabled/smart-lamp-assistant.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

cd "${REMOTE_APP_DIR}"
docker compose up -d --build
EOF

echo "Done."
echo "APK: ${PUBLIC_BASE_URL}/SmartLampAssistant.apk"
echo "Download page: ${PUBLIC_BASE_URL}/download.html"
echo "Health: ${PUBLIC_BASE_URL}/health"
