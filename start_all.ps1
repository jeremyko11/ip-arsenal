# IP Arsenal Launcher (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  IP Arsenal + MediaCrawler Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Starting MediaCrawler (port 8080)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\P-workplace\MediaCrawler-main'; uvicorn api.main:app --port 8080 --reload --host 0.0.0.0" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting IP Arsenal (port 8766)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\backend'; python start_server.py" -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Both services started!" -ForegroundColor Green
Write-Host "  Open: http://localhost:8766" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
