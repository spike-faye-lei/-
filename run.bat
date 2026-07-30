@echo off
chcp 65001 >nul
echo ===================================
echo  智能厨房助手 - 后端服务启动
echo ===================================
echo.
cd /d "D:\SmartKitchen"
echo 启动 API 服务...
echo.
echo 本地访问: http://127.0.0.1:8686
echo.
D:\SmartKitchen\venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8686 --reload
pause
