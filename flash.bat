@echo off
:: flash.bat — Windows wrapper for flash.sh
:: Finds Git Bash or WSL and runs flash.sh through it.
setlocal

set "SCRIPT=%~dp0flash.sh"
set "BASH="

:: Try Git Bash (common install locations)
if exist "%ProgramFiles%\Git\bin\bash.exe"         set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if exist "%ProgramFiles(x86)%\Git\bin\bash.exe"    set "BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "BASH=%LocalAppData%\Programs\Git\bin\bash.exe"

if not "%BASH%"=="" (
    "%BASH%" "%SCRIPT%"
    exit /b %ERRORLEVEL%
)

:: Fall back to WSL
where wsl >nul 2>&1
if %ERRORLEVEL% equ 0 (
    wsl bash "$(wslpath '%SCRIPT%')"
    exit /b %ERRORLEVEL%
)

echo ERROR: Could not find Git Bash or WSL.
echo Install Git for Windows ^(https://git-scm.com^) or enable WSL, then retry.
exit /b 1
