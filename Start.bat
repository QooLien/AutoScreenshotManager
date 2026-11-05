@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3.13 -m venv .venv
    if errorlevel 1 goto python_error
)

fc /b requirements.txt ".venv\asm-installed-requirements.txt" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto install_error
    copy /y requirements.txt ".venv\asm-installed-requirements.txt" >nul
    if errorlevel 1 goto install_error
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 goto startup_error
exit /b 0

:python_error
echo Could not create the virtual environment. Install Python 3.13 64-bit with the Windows Python launcher.
goto failed

:install_error
echo Could not install dependencies. Check the pip error above.
goto failed

:startup_error
echo Auto Screenshot Manager could not start. Check the error above.

:failed
pause
exit /b 1
