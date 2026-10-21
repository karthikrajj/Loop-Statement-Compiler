@echo off
echo ==============================================
echo Running Loop Compiler Backend Tests
echo ==============================================

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -m unittest tests/test_backend.py
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m unittest tests/test_backend.py
    exit /b %ERRORLEVEL%
)

echo ERROR: Python is not found on PATH.
exit /b 1
