@echo off
title AuraFlow - Premium Gesture Control
cd /d "%~dp0"
if exist ".\venv\Scripts\python.exe" (
    call .\venv\Scripts\python.exe start_auraflow.py
) else if exist "..\venv\Scripts\python.exe" (
    call ..\venv\Scripts\python.exe start_auraflow.py
) else (
    call python start_auraflow.py
)
pause
