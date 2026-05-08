#!/bin/bash

# Dependency Resolver Agent - Quick Setup Script
# This script sets up the project using UV for fast dependency management

set -e  # Exit on error

echo "🚀 Dependency Resolver Agent - Setup Script"
echo "==========================================="
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed."
    echo ""
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
    echo "✅ UV installed! Please restart your terminal and run this script again."
    exit 1
fi

echo "✅ UV is installed: $(uv --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d ".venv" ]; then
    uv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies with UV..."
uv sync
echo "✅ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "To use LLM features, create .env with:"
    echo ""
    echo "AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
    echo "AZURE_OPENAI_API_VERSION=2025-01-01-preview"
    echo "AZURE_OPENAI_CHATGPT_DEPLOYMENT=gpt-4o"
    echo "AZURE_OPENAI_API_KEY=your_api_key"
    echo ""
    echo "Or use Azure AD:"
    echo ""
    echo "AZURE_TENANT_ID=your_tenant_id"
    echo "AZURE_CLIENT_ID=your_client_id"
    echo "AZURE_CLIENT_SECRET=your_client_secret"
    echo ""
else
    echo "✅ .env file found"
fi

echo ""
echo "=========================================="
echo "✨ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1️⃣  Activate virtual environment (if not already):"
echo "   source .venv/bin/activate"
echo ""
echo "2️⃣  Add Azure OpenAI credentials to .env file"
echo ""
echo "3️⃣  Start the server:"
echo "   uv run uvicorn main:app --reload"
echo ""
echo "4️⃣  Open frontend in another terminal:"
echo "   open ../frontend/index.html"
echo ""
echo "5️⃣  Start resolving dependencies!"
echo ""
echo "For more info, see UV_SETUP.md"
echo ""
