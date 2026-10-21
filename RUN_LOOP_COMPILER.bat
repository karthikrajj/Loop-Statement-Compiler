@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Loop Compiler — Minimal Portable Launcher
:: Starts the Flask web server and automatically opens the user interface.
:: ============================================================================

title Loop Compiler -- C Loop Syntax Analyzer
cd /d "%~dp0"

echo ============================================================
echo           Loop Compiler -- Portable Launcher
echo ============================================================
echo.

:: 1. Detect Python executable
set "PY_CMD="

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto check_python_done
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py"
    goto check_python_done
)

:: Search typical local user install paths if not in PATH
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto check_python_done
    )
)

:check_python_done
if "%PY_CMD%"=="" (
    echo [ERROR] Python 3 was not detected on this computer.
    echo.
    echo Please install Python 3 from: https://www.python.org/downloads/
    echo Be sure to check the box "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check for required Flask package
%PY_CMD% -c "import flask" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Flask package is not yet installed in your Python environment.
    echo [INFO] Installing dependencies from requirements.txt...
    echo.
    %PY_CMD% -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [ERROR] Failed to install required dependencies.
        echo Please ensure you have internet access and run:
        echo    %PY_CMD% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
)

:: 3. Check C compiler executable status
if not exist "compiler\compiler.exe" (
    echo [NOTICE] Native C compiler binary not found at compiler\compiler.exe.
    echo The web app will start in Demo Mode [Simulated Analysis].
    echo To connect the real C compiler, run compiler\build.bat with GCC or Clang.
    echo.
) else (
    echo [OK] Native C compiler binary found: compiler\compiler.exe
)

:: 4. Schedule opening default browser to http://127.0.0.1:5000
echo [INFO] Starting web application server...
echo [INFO] Opening http://127.0.0.1:5000 in your default browser...
echo.
echo Press Ctrl+C in this window at any time to stop the server.
echo ============================================================
echo.

start "" cmd /c "ping -n 3 127.0.0.1 >nul & start http://127.0.0.1:5000"

:: 5. Launch the Flask application
%PY_CMD% app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application server stopped with error code %ERRORLEVEL%.
    pause
)
