# Dependency Resolver Agent - Setup Script for Windows
# This script sets up the project using UV for fast dependency management

Write-Host "🚀 Dependency Resolver Agent - Setup Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if UV is installed
$uvExists = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)

if (-not $uvExists) {
    Write-Host "❌ UV is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing UV..." -ForegroundColor Yellow

    try {
        powershell -ExecutionPolicy BypassCurrentUser -c "irm https://astral.sh/uv/install.ps1 | iex"
        Write-Host ""
        Write-Host "✅ UV installed! Please restart PowerShell and run this script again." -ForegroundColor Green
        exit 1
    } catch {
        Write-Host "❌ Failed to install UV. Please install manually:" -ForegroundColor Red
        Write-Host "   https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
        exit 1
    }
}

$uvVersion = uv --version
Write-Host "✅ UV is installed: $uvVersion" -ForegroundColor Green
Write-Host ""

# Create virtual environment
Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan

if (-not (Test-Path ".\.venv")) {
    uv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"
Write-Host "✅ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "📥 Installing dependencies with UV..." -ForegroundColor Cyan
uv sync
Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".\.env")) {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To use LLM features, create .env with:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
    Write-Host "AZURE_OPENAI_API_VERSION=2025-01-01-preview"
    Write-Host "AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-4o"
    Write-Host "AZURE_OPENAI_API_KEY=your_api_key"
    Write-Host ""
    Write-Host "Or use Azure AD:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "AZURE_TENANT_ID=your_tenant_id"
    Write-Host "AZURE_CLIENT_ID=your_client_id"
    Write-Host "AZURE_CLIENT_SECRET=your_client_secret"
    Write-Host ""
} else {
    Write-Host "✅ .env file found" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✨ Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1️⃣  Activate virtual environment (if not already):" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "2️⃣  Add Azure OpenAI credentials to .env file" -ForegroundColor White
Write-Host ""
Write-Host "3️⃣  Start the server:" -ForegroundColor White
Write-Host "   uv run uvicorn main:app --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "4️⃣  Open frontend in another terminal:" -ForegroundColor White
Write-Host "   start ../frontend/index.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "5️⃣  Start resolving dependencies!" -ForegroundColor White
Write-Host ""
Write-Host "For more info, see UV_SETUP.md" -ForegroundColor Yellow
Write-Host ""
