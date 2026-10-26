@echo off
setlocal enabledelayedexpansion
title Half a Doodle Launcher

echo ===================================================
echo             Half a Doodle - Launching
echo ===================================================
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM 1. Detect Python
set "PYTHON_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ to run the local server.
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_CMD%

REM 2. Check and start Ollama (Optional Vision Narration Dependency)
where ollama >nul 2>&1
if !errorlevel! equ 0 (
    netstat -a -n -o | findstr /c:":11434 " | findstr /i /c:"LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Ollama is already running on port 11434.
    ) else (
        echo [INFO] Starting Ollama server - vision narration dependency...
        set "OLLAMA_ORIGINS=*"
        start "HalfADoodle-Ollama" ollama serve
        REM Record marker file so stop.bat knows Ollama was started by this launcher
        echo 1 > "%~dp0.ollama_started"
    )
) else (
    echo [INFO] Ollama not found in PATH - vision narration will be disabled.
)

REM 3. Check and start Python HTTP Server (Port 8000)
netstat -a -n -o | findstr /c:":8000 " | findstr /i /c:"LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo [INFO] Web server is already running on port 8000.
) else (
    echo [INFO] Starting local static server on http://localhost:8000...
    start "HalfADoodle-Server" %PYTHON_CMD% -m http.server 8000
)

REM 4. Wait for server to initialize
echo [INFO] Waiting for server initialization...
ping -n 3 127.0.0.1 >nul

REM 5. Open browser
echo [INFO] Opening browser to http://localhost:8000/index.html...
start http://localhost:8000/index.html

echo.
echo ===================================================
echo Half a Doodle is running!
echo Local URL: http://localhost:8000/index.html
echo.
echo To close the application and its dependencies, run:
echo    stop.bat (or close.bat)
echo ===================================================
echo.
echo Press any key to close this launcher window [app will stay running]...
pause >nul
