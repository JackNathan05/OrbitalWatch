@echo off
title OrbitalWatch - Shutting Down
echo ============================================
echo   OrbitalWatch - Stopping All Services
echo ============================================
echo.

cd /d "%~dp0"

:: Kill backend (uvicorn)
echo [1/3] Stopping backend...
taskkill /f /fi "WINDOWTITLE eq OrbitalWatch-API" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do taskkill /f /pid %%p >nul 2>&1

:: Kill frontend (next dev)
echo [2/3] Stopping frontend...
taskkill /f /fi "WINDOWTITLE eq OrbitalWatch-Frontend" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do taskkill /f /pid %%p >nul 2>&1

:: Stop Docker containers (stop, not down — preserves data)
echo [3/3] Stopping Docker containers...
docker compose stop 2>nul

echo.
echo   All services stopped.
echo ============================================
pause
