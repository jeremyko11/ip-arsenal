@echo off
chcp 65001 >nul
cd /d d:\P-workplace\MediaCrawler-main
uvicorn api.main:app --port 8080 --reload --host 0.0.0.0
