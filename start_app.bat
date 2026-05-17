@echo off
echo Stopping existing processes...

:: Kill process on port 8000 (Backend)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

:: Kill process on port 5173 (Frontend)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo Starting Mockup Generator...

:: Start Backend from project root so generated folders stay writable
start cmd /k "python -m uvicorn backend.main:app --reload --port 8000"

:: Wait a moment for backend
timeout /t 3 /nobreak >nul

:: Start Frontend
start cmd /k "cd frontend && npm run dev"

echo Application started!
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8000
