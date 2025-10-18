# Automated Deployment Script for Personal AI Diary Journal
# This script automates the deployment process for Render.com

param(
    [string]$Message = "",
    [switch]$Force,
    [switch]$Status
)

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Blue = "Blue"
$Cyan = "Cyan"

function Write-Colored {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Show-Header {
    Write-Colored "🚀 Personal AI Diary Journal - Automated Deployment" $Cyan
    Write-Colored "================================================" $Cyan
    Write-Host ""
}

function Check-Git-Status {
    Write-Colored "📋 Checking git status..." $Blue

    $gitStatus = git status --porcelain

    if ($LASTEXITCODE -ne 0) {
        Write-Colored "❌ Git command failed. Are you in a git repository?" $Red
        exit 1
    }

    if ($gitStatus -and !$Force) {
        Write-Colored "📝 Uncommitted changes detected:" $Yellow
        Write-Host $gitStatus
        $response = Read-Host "Continue with deployment? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Colored "Deployment cancelled." $Yellow
            exit 0
        }
    } elseif (!$gitStatus) {
        Write-Colored "✅ No changes to deploy." $Green
        exit 0
    }
}
}

function Deploy-Application {
    Write-Colored "🔄 Starting deployment process..." $Blue

    # Add all changes
    Write-Colored "📦 Adding changes..." $Blue
    git add .
    if ($LASTEXITCODE -ne 0) {
        Write-Colored "❌ Failed to add changes." $Red
        exit 1
    }

    # Commit with message
    if (!$Message) {
        $Message = Read-Host "Enter commit message (or press Enter for default)"
        if (!$Message) {
            $Message = "feat: Update application"
        }
    }

    Write-Colored "💾 Committing changes..." $Blue
    git commit -m $Message
    if ($LASTEXITCODE -ne 0) {
        Write-Colored "❌ Failed to commit changes." $Red
        exit 1
    }

    # Push to trigger deployment
    Write-Colored "🚀 Pushing to GitHub (this will trigger Render deployment)..." $Blue
    git push origin main

    if ($LASTEXITCODE -ne 0) {
        Write-Colored "❌ Failed to push to GitHub." $Red
        Write-Colored "💡 Note: This is normal if you're not connected to the internet" $Yellow
        Write-Colored "   or if there are no changes to push." $Yellow
    } else {
        Write-Colored "✅ Successfully pushed to GitHub!" $Green
        Write-Colored "🔄 Render deployment should start automatically..." $Blue
    }
}

function Check-Deployment-Status {
    Write-Colored "🔍 Checking deployment status..." $Blue

    try {
        $response = Invoke-WebRequest -Uri "https://personal-ai-diary-journal.onrender.com" -TimeoutSec 10 -ErrorAction SilentlyContinue

        if ($response.StatusCode -eq 200) {
            Write-Colored "✅ Application is live and responding!" $Green
            Write-Colored "🌐 URL: https://personal-ai-diary-journal.onrender.com" $Cyan
        } else {
            Write-Colored "⚠️ Application responded with status: $($response.StatusCode)" $Yellow
        }
    } catch {
        Write-Colored "⏳ Deployment may still be in progress..." $Yellow
        Write-Colored "🔄 Render typically takes 1-2 minutes to deploy." $Blue
        Write-Colored "💡 Check back in a few minutes!" $Cyan
    }
}

function Show-Usage {
    Write-Colored "📖 Usage:" $Cyan
    Write-Host "  .\deploy.ps1                    # Interactive mode"
    Write-Host "  .\deploy.ps1 -Message 'commit message'  # With custom message"
    Write-Host "  .\deploy.ps1 -Force             # Skip confirmation prompts"
    Write-Host "  .\deploy.ps1 -Status           # Check deployment status only"
    Write-Host ""
    Write-Colored "📝 Examples:" $Cyan
    Write-Host "  .\deploy.ps1 -Message 'fix: database initialization'"
    Write-Host "  .\deploy.ps1 -Force -Message 'feat: add new feature'"
    Write-Host ""
}

# Main execution
Show-Header

if ($Status) {
    Check-Deployment-Status
    exit 0
}

# Check if we're in a git repository
if (!(Test-Path ".git")) {
    Write-Colored "❌ Not in a git repository!" $Red
    Write-Colored "💡 Make sure you're in the correct directory." $Yellow
    exit 1
}

Check-Git-Status
Deploy-Application

Write-Host ""
Write-Colored "🎉 Deployment process completed!" $Green
Write-Colored "🔄 Your changes are now deploying to Render.com" $Blue

# Check deployment status after a short delay
Start-Sleep -Seconds 3
Check-Deployment-Status

Write-Host ""
Write-Colored "💡 Pro Tips:" $Cyan
Write-Host "  - Render deployments typically take 1-2 minutes"
Write-Host "  - Check https://dashboard.render.com for deployment logs"
Write-Host "  - Use '.\deploy.ps1 -Status' to check if deployment completed"
Write-Host ""
