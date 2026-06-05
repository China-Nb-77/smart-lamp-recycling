@echo off
echo ============================================
echo  smart-lamp-recycling 前后端启动脚本
echo ============================================

set PROJECT_DIR=%~dp0
set PYTHON=C:\Users\LEGION\.workbuddy\binaries\python\envs\default\Scripts\python.exe
set NODE=C:\Users\LEGION\.workbuddy\binaries\node\versions\22.22.2\node.exe
set NPM=C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js

echo.
echo [1/2] 启动后端 FastAPI (端口 8000)...
cd /D "%PROJECT_DIR%"
start "Backend - FastAPI 8000" cmd /K "set REDIS_URL=fakeredis:// && set DATABASE_URL=sqlite:///./dev.db && set AI_LIGHT_WORKFLOW_MODE=mock && set AI_LIGHT_PAYMENT_MODE=mock && "%PYTHON%" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"

echo.
echo [2/2] 启动前端 Vite (端口 5173)...
cd /D "%PROJECT_DIR%frontend"
start "Frontend - Vite 5173" cmd /K ""%NODE%" "%NPM%" run dev"

echo.
echo ============================================
echo  启动完成！
echo  后端 API:  http://localhost:8000
echo  后端文档:  http://localhost:8000/docs
echo  前端页面:  http://localhost:5173
echo ============================================
pause
