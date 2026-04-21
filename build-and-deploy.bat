@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-and-deploy.ps1"
exit /b %ERRORLEVEL%
