@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 招聘智能体 Demo

echo ==========================================
echo   招聘智能体 Demo - 一键启动
echo ==========================================

rem 检查依赖，缺失则自动安装
py -3.12 -c "import gradio, pypdf, docx, requests" >nul 2>&1
if errorlevel 1 (
    echo [1/2] 首次运行，正在安装依赖（约1-2分钟）...
    py -3.12 -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络后重试
        pause
        exit /b 1
    )
    echo       依赖安装完成
) else (
    echo [1/2] 依赖已就绪
)

echo [2/2] 启动服务，浏览器将自动打开 http://localhost:7860
echo       关闭本窗口即停止服务
echo ------------------------------------------
start "" http://localhost:7860
py -3.12 app.py
pause
