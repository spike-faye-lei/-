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
    echo [1/3] 首次运行，正在安装依赖（约1-2分钟）...
    py -3.12 -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络后重试
        pause
        exit /b 1
    )
    echo       依赖安装完成
) else (
    echo [1/3] 依赖已就绪
)

rem 备份数据库：每次启动前按时间戳存一份到 backups\（防止招聘数据意外丢失）
echo [2/3] 备份数据库 recruit.db -^> backups\
if not exist backups mkdir backups
if exist recruit.db (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set ds=%%i
    copy /y recruit.db "backups\recruit-%ds%.db" >nul
    echo       已备份：backups\recruit-%ds%.db
) else (
    echo       首次运行，暂无数据库可备份
)

echo [3/3] 启动服务，浏览器将自动打开 http://localhost:7860
echo       关闭本窗口即停止服务
echo ------------------------------------------
start "" http://localhost:7860
py -3.12 app.py
pause
