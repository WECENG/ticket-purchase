@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   ??????? (????)
echo ========================================
echo.
echo   ??: http://127.0.0.1:8765
echo   ??: http://127.0.0.1:5173
echo.

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

start "????-??" cmd /c "python -m console.server"
timeout /t 2 >nul
start "????-??" cmd /c "cd console\web && npx vite --host"

echo.
echo ???????:
echo   - ??: http://127.0.0.1:8765
echo   - ??: http://127.0.0.1:5173
echo.
pause
