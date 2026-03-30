@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PATH=C:\Users\jeremyko11\AppData\Local\Programs\Microsoft\jdk-11.0.30.7-hotspot\bin;%PATH%
echo IP Arsenal is starting...
echo Visit: http://localhost:8765
start "" "http://localhost:8765"
cd /d "%~dp0backend"
"C:\Users\jeremyko11\AppData\Local\Programs\Python\Python312\python.exe" main.py

