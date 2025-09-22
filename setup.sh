#!/bin/bash

# Thumbtack Automation Bot Setup Script

set -e

echo "🚀 Setting up Thumbtack Automation Bot..."

# Check if Python 3.11+ is installed
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "✅ Python $python_version is installed"
else
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p logs

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys and configuration"
fi

# Create docker ignore file
if [ ! -f ".dockerignore" ]; then
    echo "🐳 Creating .dockerignore..."
    cat > .dockerignore << EOF
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
.venv/
.env
.git/
.gitignore
README.md
.dockerignore
Dockerfile
docker-compose.yml
logs/
*.log
.DS_Store
mock_*.json
token.pickle
EOF
fi

# Create gitignore file
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << EOF
# Environment files
.env
credentials.json
token.pickle

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
logs/
*.log

# Mock data (optional, remove if you want to version control test data)
mock_leads.json
mock_messages.json

# OS
.DS_Store
Thumbs.db
EOF
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. 🔑 Edit .env file with your API keys:"
echo "   - Get OpenAI API key from https://platform.openai.com/"
echo "   - Set up Google Calendar API and download credentials.json"
echo ""
echo "2. 📅 Set up Google Calendar API:"
echo "   - Go to https://console.cloud.google.com/"
echo "   - Enable Google Calendar API"
echo "   - Create OAuth 2.0 credentials"
echo "   - Download credentials.json to project root"
echo ""
echo "3. 🚀 Run the bot:"
echo "   - Test run: python main.py --once"
echo "   - Daemon mode: python main.py --daemon"
echo "   - Docker: docker-compose up -d"
echo ""
echo "4. 📊 Monitor logs:"
echo "   - Local: tail -f logs/thumbtack_bot.log"
echo "   - Docker: docker-compose logs -f"
echo ""
echo "For more information, check README.md"