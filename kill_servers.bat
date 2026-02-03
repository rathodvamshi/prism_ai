@echo off
echo Killing Node.js processes...
taskkill /F /IM node.exe
echo Killing Python/Uvicorn processes...
taskkill /F /IM python.exe
taskkill /F /IM uvicorn.exe
echo All servers stopped.
pause
