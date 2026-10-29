@echo off
REM Ace Gotchi launcher. Use "Ace Gotchi.vbs" for a console-free start.
cd /d "%~dp0"

set "PYW="
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%i"
)
if defined PYEXE (
    for %%d in ("%PYEXE%") do set "CAND=%%~dpdpythonw.exe"
)
if defined CAND if exist "%CAND%" set "PYW=%CAND%"

if defined PYW (
    start "" "%PYW%" "%~dp0main.py"
) else (
    where pythonw.exe >nul 2>nul && (start "" pythonw "%~dp0main.py") || (python "%~dp0main.py")
)
