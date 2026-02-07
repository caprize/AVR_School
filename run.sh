#!/bin/bash

# Chemistry Bot - Run Script
# Starts the bot with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Chemistry Bot Launcher${NC}"
echo "================================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found${NC}"
    echo "Running setup..."
    bash setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Check if Redis is running
echo -e "${YELLOW}Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${RED}❌ Redis is not running${NC}"
    echo -e "${YELLOW}Starting Redis...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew services start redis 2>/dev/null || redis-server --daemonize yes
    else
        # Linux
        redis-server --daemonize yes
    fi
    
    sleep 2
    
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis${NC}"
        echo "Please install Redis manually:"
        echo "  macOS: brew install redis"
        echo "  Linux: sudo apt-get install redis-server"
        exit 1
    fi
fi

# Check config.json
if [ ! -f "config.json" ]; then
    echo -e "${RED}❌ config.json not found!${NC}"
    exit 1
fi

# Check if bot token is configured
TOKEN=$(grep -o '"bot_token": "[^"]*"' config.json | head -1)
if [[ "$TOKEN" == *"YOUR_BOT_TOKEN_HERE"* ]] || [[ -z "$TOKEN" ]]; then
    echo -e "${RED}❌ Bot token not configured in config.json${NC}"
    echo "Please get a token from @BotFather and update config.json"
    exit 1
fi

echo -e "${GREEN}✅ Configuration OK${NC}"
echo ""
echo -e "${YELLOW}Starting Chemistry Bot...${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo ""

# Run the bot
python bot.py
