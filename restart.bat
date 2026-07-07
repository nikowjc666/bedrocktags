@echo off
chcp 65001 >nul
cd /d D:\bedrock-inference-profiles
echo 正在停止旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5001.*LISTENING"') do taskkill /f /pid %%a 2>nul
echo 正在启动项目...
call .venv\Scripts\activate.bat && python app.py
pause
