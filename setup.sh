#!/bin/bash

# Chemistry Bot - Setup Script
# This script sets up the environment for local testing

echo "🚀 Setting up Chemistry Bot for local testing..."

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis is not installed. Installing..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install redis
        brew services start redis
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux (Ubuntu/Debian)
        sudo apt-get update
        sudo apt-get install -y redis-server
        sudo systemctl start redis-server
    else
        echo "❌ Unsupported OS. Please install Redis manually."
        exit 1
    fi
else
    echo "✅ Redis is already installed"
fi

# Start Redis if not running
redis-cli ping 2>/dev/null || (
    echo "Starting Redis..."
    redis-server --daemonize yes
)

# Check Python version
python3 --version

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Get a bot token from @BotFather in Telegram"
echo "2. Update config.json with your bot token and admin ID"
echo "3. Run: python bot.py"
echo ""
echo "To stop Redis later, run: redis-cli shutdown"
