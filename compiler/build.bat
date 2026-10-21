@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo Building C Loop Compiler
echo ==============================================

:: If clang or gcc is not directly in PATH, add typical WinGet install path
set "WG_BIN=C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\MartinStorsjo.LLVM-MinGW.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\llvm-mingw-20260908-ucrt-x86_64\bin"
if exist "%WG_BIN%\clang.exe" (
    set "PATH=%WG_BIN%;%PATH%"
)

where clang >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Compiling with clang...
    clang -std=c99 -Wall -Wextra -O2 compiler.c -o compiler.exe
    goto check_result
)

where gcc >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Compiling with gcc...
    gcc -std=c99 -Wall -Wextra -O2 compiler.c -o compiler.exe
    goto check_result
)

where cl >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Compiling with MSVC cl...
    cl /W3 /O2 compiler.c /Fe:compiler.exe
    goto check_result
)

echo ERROR: No C compiler (clang, gcc, or cl) found.
echo Please install GCC / MinGW or LLVM Clang.
exit /b 1

:check_result
if exist compiler.exe (
    echo [SUCCESS] compiler.exe built successfully!
    exit /b 0
) else (
    echo [FAILED] Compilation failed.
    exit /b 1
)
