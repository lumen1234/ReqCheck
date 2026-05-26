@echo off
cd /d "%~dp0..\frontend"
call npm run build
echo Frontend built to frontend\dist
