@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    call :create_venv
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

:create_venv
py -3.13 -c "import struct, sys; sys.exit(struct.calcsize('P') != 8)" >nul 2>&1
if not errorlevel 1 (
    py -3.13 -m venv .venv
    exit /b
)
python -c "import struct, sys; sys.exit(sys.version_info[:2] != (3, 13) or struct.calcsize('P') != 8)" >nul 2>&1
if errorlevel 1 exit /b 1
python -m venv .venv
exit /b

:python_error
echo Could not create the virtual environment with Python 3.13 64-bit.
echo If Python is installed, open PowerShell and run py -0p and python --version.
goto failed

:install_error
echo Could not install dependencies. Check the pip error above.
goto failed

:startup_error
echo Auto Screenshot Manager could not start. Check the error above.

:failed
pause
exit /b 1
