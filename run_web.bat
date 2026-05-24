@echo off
chcp 65001 >nul
cd /d "%~dp0damai"
echo ========================================
echo   大麦抢票 - Web端启动
echo ========================================
echo.
echo 请确保已修改 damai\config.json 配置
echo  - target_url: 目标演出URL
echo  - users: 观演人姓名
echo  - city: 城市
echo  - dates: 场次日期
echo  - prices: 票面价格
echo.
echo if_commit_order=false 时仅模拟流程，不会真正下单
echo.
pause
echo.
python damai.py
pause
