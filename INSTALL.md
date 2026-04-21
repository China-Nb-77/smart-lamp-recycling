# 智能选灯助手 APK 打包与阿里云部署

## 当前集成内容

- APK 内置的是仓库里的现有主线前端：`frontend/`
- 线上部署的是仓库里的现有主线后端：`backend/`
- APK 构建容器：Capacitor Android
- 后端部署方式：Docker Compose
- 对外访问方式：Nginx 80 端口反向代理 + APK / `download.html` 静态下载

## 先决条件

### 本机

- Node.js 20+
- Java 17+
- Android SDK / Android Studio
- `ssh`、`scp`
- Windows 运行 `build-and-deploy.bat`
- macOS / Linux 运行 `build-and-deploy.sh`

### 阿里云服务器

- Ubuntu / Debian 系 Linux
- 已开放 80 端口
- 能用 `root` 或有 sudo 权限的用户 SSH 登录

脚本会自动在服务器上安装：

- `docker.io`
- `docker-compose-plugin`
- `nginx`

## 需要修改的变量

### Windows

```bat
set SERVER_IP=114.215.177.52
set SERVER_USER=root
set SERVER_SSH_PORT=22
set SERVER_PATH=/var/www/html
set PUBLIC_BASE_URL=http://114.215.177.52
set SESSION_SECRET=请改成复杂字符串
build-and-deploy.bat
```

### macOS / Linux

```bash
SERVER_IP="114.215.177.52" \
SERVER_USER="root" \
SERVER_SSH_PORT="22" \
SERVER_PATH="/var/www/html" \
PUBLIC_BASE_URL="http://114.215.177.52" \
SESSION_SECRET="请改成复杂字符串" \
./build-and-deploy.sh
```

## 脚本会做什么

1. 安装根目录 Capacitor 依赖和 `frontend` 依赖
2. 用 `PUBLIC_BASE_URL` 构建 `frontend/dist`
3. 初始化或同步 Android 工程
4. 构建 `delivery/SmartLampAssistant.apk`
5. 打包最小后端运行集并上传到服务器
6. 在服务器安装 Docker / Nginx
7. 启动 Redis、Postgres、FastAPI 后端
8. 配置 Nginx：
   - `/SmartLampAssistant.apk`
   - `/download.html`
   - `/health`
   - `/preflight`
   - `/quote`
   - `/quote-upload`
   - `/recommend`
   - `/classify`
   - `/classify-upload`
   - `/classify-lamp`
   - `/classify-lamp-upload`
   - `/catalog-image`
   - `/agent/*`

## 产物

- `delivery/SmartLampAssistant.apk`
- `delivery/smart-lamp-backend.tar.gz`
- `http://你的服务器地址/SmartLampAssistant.apk`
- `http://你的服务器地址/download.html`
- `http://你的服务器地址/health`

## 默认运行模式说明

脚本默认使用：

```text
WORKFLOW_MODE=mock
PAYMENT_MODE=mock
```

这和仓库当前后端的默认可运行方式保持一致：

- 推荐目录与下单链路可用
- 旧灯上传与回收报价会走 review fallback
- 支付流程走 mock 模式

如果你后续已经准备好真实模型和支付配置，可以在运行脚本前自行覆盖：

```bash
WORKFLOW_MODE=real
PAYMENT_MODE=real
```

## 验证清单

1. 打开 `http://你的服务器地址/health`，确认返回 JSON
2. 打开 `http://你的服务器地址/download.html`，确认二维码和 APK 链接正常
3. 手机上安装 APK
4. 登录后进入聊天页
5. 上传旧灯图片或直接体验推荐、下单、电子单据流程

## 常见问题

### APK 能打开，但接口请求失败

- 检查 `PUBLIC_BASE_URL` 是否写成了服务器公网地址
- 检查阿里云安全组是否放行 80 端口
- 检查 Nginx 是否成功重载

### APK 下载正常，但安装失败

- 检查服务器上的 `SmartLampAssistant.apk` 是否上传完整
- 检查手机是否允许安装未知来源应用

### Android 里请求 HTTP 被拦截

- 脚本会自动给 AndroidManifest 打开 `usesCleartextTraffic`
- 如果你后续改成 HTTPS，可以继续沿用当前脚本
