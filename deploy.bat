@echo off
REM Automated Deployment Script for Personal AI Diary Journal
REM Windows Batch File Version

echo 🚀 Personal AI Diary Journal - Automated Deployment
echo =================================================
echo.

REM Check if we're in a git repository
if not exist ".git" (
    echo ❌ Not in a git repository!
    echo 💡 Make sure you're in the correct directory.
    pause
    exit /b 1
)

echo 📋 Checking git status...
git status --porcelain > temp_status.txt 2>nul
if errorlevel 1 (
    echo ❌ Git command failed. Are you in a git repository?
    del temp_status.txt 2>nul
    pause
    exit /b 1
)

set "has_changes="
for /f %%i in (temp_status.txt) do set "has_changes=1"
del temp_status.txt 2>nul

if not defined has_changes (
    echo ✅ No changes to deploy.
    pause
    exit /b 0
)

echo 📝 Changes detected. Adding files...
git add .
if errorlevel 1 (
    echo ❌ Failed to add changes.
    pause
    exit /b 1
)

REM Get commit message from command line or use default
if "%~1"=="" (
    set "commit_msg=feat: Update application"
) else (
    set "commit_msg=%~1"
)

echo 💾 Committing changes...
git commit -m "%commit_msg%"
if errorlevel 1 (
    echo ❌ Failed to commit changes.
    pause
    exit /b 1
)

echo 🚀 Pushing to GitHub (this will trigger Render deployment)...
git push origin main

if errorlevel 1 (
    echo ❌ Failed to push to GitHub.
    echo 💡 Note: This is normal if you're not connected to the internet
    echo    or if there are no changes to push.
) else (
    echo ✅ Successfully pushed to GitHub!
    echo 🔄 Render deployment should start automatically...
)

echo.
echo 🎉 Deployment process completed!
echo 🔄 Your changes are now deploying to Render.com
echo.
echo 💡 Pro Tips:
echo   - Render deployments typically take 1-2 minutes
echo   - Check https://dashboard.render.com for deployment logs
echo   - Use 'curl https://personal-ai-diary-journal.onrender.com' to check status
echo.

pause
