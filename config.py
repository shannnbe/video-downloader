import os
from pathlib import Path

# Telegram Bot Token (from environment variable)
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

# Download settings
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
MAX_FILE_SIZE_MB = 50  # Telegram's bot limit
DOWNLOAD_TIMEOUT = 120  # 2 minutes timeout for downloads

# Ensure downloads directory exists
Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)
