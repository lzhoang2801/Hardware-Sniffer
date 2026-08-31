@echo off
echo ========================================
echo   Send Hardware-Sniffer updates to GitHub
echo ========================================
echo.
echo Opening Fork page in your browser...
start https://github.com/lzhoang2801/Hardware-Sniffer
echo.
echo Click the Fork button (top right), then come back here.
echo.
pause

set /p USERNAME="Enter your GitHub username: "
if "%USERNAME%"=="" (
    echo Error: Username required.
    pause
    exit /b 1
)

echo.
echo Step 1: Cloning your fork...
cd ..
if exist Hardware-Sniffer-Git (
    echo Folder Hardware-Sniffer-Git already exists. Remove it first or use a different name.
    pause
    exit /b 1
)
git clone https://github.com/%USERNAME%/Hardware-Sniffer.git Hardware-Sniffer-Git
if errorlevel 1 (
    echo.
    echo ERROR: Clone failed. Make sure you:
    echo   1. Created a fork at https://github.com/lzhoang2801/Hardware-Sniffer - click Fork
    echo   2. Your username is correct: %USERNAME%
    pause
    exit /b 1
)

echo.
echo Step 2: Copying your modified files...
xcopy /E /Y "Hardware-Sniffer-main\*" "Hardware-Sniffer-Git\"

echo.
echo Step 3: Creating branch and committing...
cd Hardware-Sniffer-Git
git checkout -b feature/collecte-complete
git add .
git commit -m "feat: Add RAM, MAC, ports, SMBIOS collection and bug fixes"

echo.
echo Step 4: Pushing to GitHub...
git push -u origin feature/collecte-complete

echo.
echo ========================================
echo   Done!
echo   Go to: https://github.com/%USERNAME%/Hardware-Sniffer
echo   Click "Compare and pull request"
echo ========================================
pause
