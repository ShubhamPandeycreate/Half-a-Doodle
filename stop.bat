@echo off
setlocal enabledelayedexpansion
title Half a Doodle - Stopping

echo ===================================================
echo         Half a Doodle - Stopping Services
echo ===================================================
echo.

cd /d "%~dp0"

REM 1. Stop Python Web Server (Port 8000)
echo [1/2] Stopping local web server on port 8000...
for /f "tokens=5" %%a in ('netstat -a -n -o ^| findstr /c:":8000 " ^| findstr /i /c:"LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
taskkill /FI "WINDOWTITLE eq HalfADoodle-Server*" /T /F >nul 2>&1
echo [OK] Web server stopped.

REM 2. Stop Ollama if it was started by start.bat, or if --all is specified
echo [2/2] Checking vision narration dependency [Ollama]...
set "STOP_OLLAMA=0"

if "%1"=="--all" set "STOP_OLLAMA=1"
if "%1"=="/all" set "STOP_OLLAMA=1"
if exist "%~dp0.ollama_started" set "STOP_OLLAMA=1"

if "!STOP_OLLAMA!"=="1" (
    echo [INFO] Stopping Ollama server...
    for /f "tokens=5" %%a in ('netstat -a -n -o ^| findstr /c:":11434 " ^| findstr /i /c:"LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    taskkill /FI "WINDOWTITLE eq HalfADoodle-Ollama*" /T /F >nul 2>&1
    taskkill /F /IM ollama.exe >nul 2>&1
    if exist "%~dp0.ollama_started" del "%~dp0.ollama_started" >nul 2>&1
    echo [OK] Ollama server stopped.
) else (
    REM Check if Ollama is currently running independently
    netstat -a -n -o | findstr /c:":11434 " | findstr /i /c:"LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Ollama was not started by start.bat and remains running.
        echo        Run 'stop.bat --all' if you want to force stop Ollama too.
    ) else (
        echo [OK] Ollama is not running.
    )
)

echo.
echo ===================================================
echo All Half a Doodle services have been stopped.
echo ===================================================
echo.
ping -n 3 127.0.0.1 >nul
