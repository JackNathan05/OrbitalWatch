@echo off
title OrbitalWatch Launcher
echo ============================================
echo   OrbitalWatch - Starting All Services
echo ============================================
echo.

cd /d "%~dp0"

:: ---- Docker ----
echo [1/5] Starting TimescaleDB + Redis...
docker compose up -d 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker failed. Is Docker Desktop running?
    pause
    exit /b 1
)
:wait_db
docker exec orbital-watch-timescaledb-1 pg_isready -U orbital -d orbitalwatch >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 /nobreak >nul
    goto wait_db
)
echo       Database ready.

:: ---- Python venv ----
if not exist "backend\venv\Scripts\activate.bat" (
    echo [2/5] Creating Python virtual environment...
    python -m venv backend\venv
    call backend\venv\Scripts\activate.bat
    pip install -r backend\requirements.txt -q
) else (
    call backend\venv\Scripts\activate.bat
)
echo       Python ready.

:: ---- Data check + load (blocking, before server starts) ----
echo [3/5] Checking data...
cd backend
python init_db.py >nul 2>&1

:: Query counts via temp files (avoids batch quoting problems)
docker exec orbital-watch-timescaledb-1 psql -U orbital -d orbitalwatch -t -A -c "SELECT COUNT(*) FROM gp_elements;" > "%TEMP%\ow_sat.txt" 2>nul
docker exec orbital-watch-timescaledb-1 psql -U orbital -d orbitalwatch -t -A -c "SELECT COUNT(*) FROM cdm;" > "%TEMP%\ow_cdm.txt" 2>nul

set SAT_COUNT=0
set /p SAT_COUNT=<"%TEMP%\ow_sat.txt"
set CDM_COUNT=0
set /p CDM_COUNT=<"%TEMP%\ow_cdm.txt"

echo       Found %SAT_COUNT% satellites, %CDM_COUNT% CDMs in database.

:: Load TLEs if needed
if %SAT_COUNT% LSS 1000 goto load_tles
echo       Satellite data already loaded.
goto check_cdms
:load_tles
echo       Loading satellite data from CelesTrak...
python ingest_all.py
echo       Loading object types from Space-Track SATCAT...
python ingest_satcat.py

:check_cdms
if %CDM_COUNT% LSS 10 goto load_cdms
echo       Conjunction data already loaded.
goto data_done
:load_cdms
echo       Loading conjunction data from Space-Track...
python ingest_cdms.py

:data_done
cd ..

:: ---- Backend ----
echo [4/5] Starting backend on :8000...
cd backend
start /b "OrbitalWatch-API" cmd /c "call venv\Scripts\activate.bat && uvicorn app.main:app --port 8000 2>&1 || pause"
cd ..
:wait_api
timeout /t 1 /nobreak >nul
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% neq 0 goto wait_api
echo       Backend ready.

:: ---- Frontend ----
if not exist "frontend\node_modules" (
    echo [5/5] Installing frontend dependencies...
    cd frontend
    npm install -q
    cd ..
)
echo [5/5] Starting frontend on :3000...
cd frontend
start /b "OrbitalWatch-Frontend" cmd /c "npm run dev 2>&1"
cd ..
:wait_frontend
timeout /t 1 /nobreak >nul
curl -s http://localhost:3000/ >nul 2>&1
if %errorlevel% neq 0 goto wait_frontend

echo.
echo ============================================
echo   OrbitalWatch is running!
echo ============================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Data refreshes automatically every 4 hours.
echo   Positions update every 60 seconds.
echo.
echo   Press any key to open in browser...
echo   Run stop.bat to shut down.
echo ============================================
pause >nul
start http://localhost:3000
pause
