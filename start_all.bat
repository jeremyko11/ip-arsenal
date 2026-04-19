@echo off
chcp 65001 >nul
title IP Arsenal Launcher

echo [1] Starting MediaCrawler on port 8080...
start "MediaCrawler" cmd /c "cd /d d:\P-workplace\MediaCrawler-main & uvicorn api.main:app --port 8080 --reload --host 0.0.0.0"

echo [2] Starting IP Arsenal on port 8766...
start "IP Arsenal" cmd /c "cd /d C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend & python main.py"

echo.
echo Done! Open http://localhost:8766
pause
