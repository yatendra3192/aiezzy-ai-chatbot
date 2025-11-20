@echo off
echo ============================================
echo  Railway Volume Download Script
echo  AIezzy Backup Tool
echo ============================================
echo.

REM Check if Railway CLI is installed
where railway >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Railway CLI not found!
    echo Installing Railway CLI...
    npm install -g @railway/cli
    echo.
)

echo Step 1: Logging into Railway...
echo This will open your browser for authentication.
echo.
railway login
if %errorlevel% neq 0 (
    echo ERROR: Login failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Linking to your Railway project...
railway link
if %errorlevel% neq 0 (
    echo ERROR: Project linking failed!
    pause
    exit /b 1
)

echo.
echo Step 3: Listing available volumes...
railway volume list
echo.

echo Step 4: Finding volume ID...
for /f "tokens=1" %%i in ('railway volume list ^| findstr /i "vol_"') do set VOLUME_ID=%%i

if "%VOLUME_ID%"=="" (
    echo ERROR: No volume found!
    echo Please enter your volume ID manually:
    set /p VOLUME_ID="Volume ID: "
)

echo Found Volume ID: %VOLUME_ID%
echo.

echo Step 5: Creating backup folder...
set BACKUP_DIR=railway_backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
mkdir "%BACKUP_DIR%"
echo Backup folder created: %BACKUP_DIR%
echo.

echo ============================================
echo  Choose Download Option:
echo ============================================
echo 1. Download EVERYTHING (11.4 GB)
echo 2. Download Conversations only (12.1 MB) - Quick!
echo 3. Download Images only (1.4 GB)
echo 4. Download Videos only (8.2 GB)
echo 5. Download Uploads only (1.8 GB)
echo ============================================
echo.
set /p CHOICE="Enter your choice (1-5): "

if "%CHOICE%"=="1" (
    echo.
    echo Downloading ENTIRE volume (11.4 GB)...
    echo This may take 10-30 minutes depending on your internet speed.
    echo.
    railway volume download %VOLUME_ID% "%BACKUP_DIR%"
) else if "%CHOICE%"=="2" (
    echo.
    echo Downloading Conversations (12.1 MB)...
    railway volume download %VOLUME_ID% "%BACKUP_DIR%" --path /app/data/conversations
) else if "%CHOICE%"=="3" (
    echo.
    echo Downloading Images (1.4 GB)...
    railway volume download %VOLUME_ID% "%BACKUP_DIR%" --path /app/data/assets
) else if "%CHOICE%"=="4" (
    echo.
    echo Downloading Videos (8.2 GB)...
    echo This may take 10-20 minutes depending on your internet speed.
    railway volume download %VOLUME_ID% "%BACKUP_DIR%" --path /app/data/videos
) else if "%CHOICE%"=="5" (
    echo.
    echo Downloading Uploads (1.8 GB)...
    railway volume download %VOLUME_ID% "%BACKUP_DIR%" --path /app/data/uploads
) else (
    echo Invalid choice! Exiting...
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Download Complete!
echo ============================================
echo.
echo Files saved to: %BACKUP_DIR%
echo.
dir "%BACKUP_DIR%" /s
echo.
echo ============================================
pause
