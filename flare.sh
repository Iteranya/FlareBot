#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the bot
python3 bot.py

# If the bot crashes, this will prevent the window from closing immediately
echo "Bot has stopped. Press Enter to exit..."
read -r
