@echo off
chcp 65001 >nul
echo ===================================
echo  DevEco Studio 安装脚本
echo ===================================
echo.
echo 步骤1: 请先手动下载最新版 DevEco Studio
echo 下载地址: https://developer.huawei.com/consumer/cn/deveco-studio/
echo.
echo 步骤2: 将下载的 ZIP 解压到 D:\DevEcoStudio
echo.
echo 步骤3: 按任意键继续...
pause >nul

if not exist "D:\DevEcoStudio\bin\devecostudio64.exe" (
    echo [!] 未找到 D:\DevEcoStudio\bin\devecostudio64.exe
    echo 请确保已将 DevEco Studio 解压到 D:\DevEcoStudio
    pause
    exit /b 1
)

echo [✓] DevEco Studio 已就绪

:: 创建桌面快捷方式
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%USERPROFILE%\Desktop\DevEco Studio.lnk'); $SC.TargetPath = 'D:\DevEcoStudio\bin\devecostudio64.exe'; $SC.WorkingDirectory = 'D:\DevEcoStudio\bin'; $SC.Description = 'DevEco Studio 6.0'; $SC.Save()"
echo [✓] 桌面快捷方式已创建

echo.
echo ===================================
echo  安装完成！
echo  双击桌面 "DevEco Studio" 图标启动
echo  原有的项目和配置仍在 AppData 中
echo ===================================
pause
