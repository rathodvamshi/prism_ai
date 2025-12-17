@echo off
echo Stopping any running Python/Uvicorn processes...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting PRISM Backend Server...
cd /d C:\Users\vamsh\Source\3_1\project_ps2\prism\prism-ai-studio\prism-backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
