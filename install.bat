@echo off
REM Quick installer for Jira Presentation Tool (Windows)

echo ==========================================
echo Jira Presentation Tool - Quick Installer
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.7 or higher from https://www.python.org/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Warning: Some dependencies may have failed to install
    echo You can try again with: pip install -r requirements.txt
)
echo Dependencies installed

REM Check if config exists
if exist .jira_environment (
    echo.
    echo Warning: Configuration file already exists
    set /p "CONTINUE=Run setup wizard anyway? [y/N]: "
    if /i not "%CONTINUE%"=="y" (
        echo Skipping setup wizard
        echo.
        echo ==========================================
        echo Installation Complete!
        echo ==========================================
        echo.
        echo Run the application:
        echo   python webapp/app.py
        echo.
        pause
        exit /b 0
    )
)

REM Run setup wizard
echo.
echo Starting configuration wizard...
echo.
python setup_wizard.py

if errorlevel 1 (
    echo.
    echo Setup wizard was cancelled or failed
    echo You can run it again with: python setup_wizard.py
    echo Or use the web setup: python webapp/app.py
    echo.
) else (
    echo.
    echo ==========================================
    echo Installation Complete!
    echo ==========================================
    echo.
    echo Run the application:
    echo   python webapp/app.py
    echo.
    echo Then visit: http://localhost:5000
    echo.
)

pause
