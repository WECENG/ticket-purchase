@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   ???????
echo ========================================
echo.
echo   ??????...
echo.

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

python -m console.server
pause
