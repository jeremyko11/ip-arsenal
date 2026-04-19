@echo off
chcp 65001 >nul
cd /d C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/ip_arsenal
start "IP Arsenal" python -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8766, log_level='warning')"
