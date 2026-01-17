# Telegram Video Downloader Bot

A Telegram bot that downloads videos from Smule, YouTube, Instagram, TikTok, Twitter, Facebook and more.

## Features

- 🎤 Downloads from Smule (primary platform)
- 📹 Supports YouTube, Instagram, TikTok, Twitter/X, Facebook
- ✅ Simple to use - just send a video link
- 🚀 Automatic video format conversion to MP4
- 🔒 Runs in Docker for security and reliability

## Quick Start

### 1. Get Your Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy your bot token (looks like: `1234567890:ABCdefGhIjKlmNoPQRsTUVwxyZ`)

### 2. Set Up the Bot

```bash
# Clone or navigate to the project directory
cd video-downloader

# Create .env file with your bot token
echo "BOT_TOKEN=YOUR_BOT_TOKEN_HERE" > .env

# Build and start the bot
docker-compose up -d

# Check if it's running
docker-compose logs -f
```

### 3. Start Using

1. Open Telegram and search for your bot (by the username you created)
2. Send `/start` to begin
3. Send any video link from supported platforms
4. Get your video!

## Supported Platforms

- ✅ Smule (smule.com)
- ✅ YouTube (youtube.com, youtu.be)
- ✅ Instagram (posts, reels, stories)
- ✅ TikTok
- ✅ Twitter/X
- ✅ Facebook

## Commands

- `/start` - Welcome message and instructions
- `/help` - Show supported platforms
- Send any video URL - Downloads the video

## Deployment Options

### Option 1: Docker (Recommended)

Already covered in Quick Start above.

**Useful commands:**
```bash
# View logs
docker-compose logs -f

# Restart bot
docker-compose restart

# Stop bot
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Option 2: Local Python (Without Docker)

```bash
# Install Python 3.10+ and ffmpeg
sudo apt install python3 python3-pip ffmpeg  # Ubuntu/Debian
# or
brew install python ffmpeg  # macOS

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export BOT_TOKEN="your_bot_token_here"

# Run the bot
python bot.py
```

### Option 3: VPS Deployment

For 24/7 availability, deploy to a VPS:

**Recommended providers:**
- Hetzner (€3-5/month)
- DigitalOcean ($6/month)
- Vultr ($5/month)
- Oracle Cloud (Free tier available)

**Requirements:**
- 1 CPU core
- 1GB RAM minimum
- 10GB storage

**Deploy:**
```bash
# On your VPS (after SSH)
cd ~
git clone <your-repo-url>
cd video-downloader

# Create .env file
nano .env
# Add: BOT_TOKEN=your_token_here
# Save: Ctrl+X, Y, Enter

# Start bot
docker-compose up -d

# Optional: Set up UFW firewall
sudo apt update
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

## Troubleshooting

### Bot not responding
```bash
# Check if container is running
docker-compose ps

# Check logs for errors
docker-compose logs -f
```

### "BOT_TOKEN environment variable is not set"
Make sure your `.env` file exists and contains your token:
```bash
cat .env
# Should show: BOT_TOKEN=123456789:ABC...
```

### Download fails for specific platform
- Smule/Instagram/TikTok may change their APIs
- Update yt-dlp: `docker-compose build --no-cache`
- Some videos may be private or geo-restricted

### File too large error
- Telegram bots can only send files up to 50MB
- Try a shorter video
- The bot automatically tries to download lower quality if available

## Updating yt-dlp

Video platforms change frequently. Update yt-dlp regularly:

```bash
# Method 1: Rebuild container (updates yt-dlp)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Method 2: Update in running container
docker exec telegram-video-bot pip install --upgrade yt-dlp
docker-compose restart
```

## File Structure

```
video-downloader/
├── bot.py              # Main bot logic
├── downloader.py       # Video download functions
├── config.py           # Configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── .env               # Your bot token (create this!)
├── .dockerignore      # Docker ignore rules
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Security Notes

- Never commit `.env` to Git (it's in `.gitignore`)
- Keep your bot token private
- The bot runs as non-root user in Docker
- No user data is stored or logged

## Maintenance

For personal/family use (5-10 videos per week):
- Update yt-dlp monthly or when downloads start failing
- Check disk space occasionally: `du -sh downloads/`
- Old temporary files are auto-cleaned after sending

## Support

If something doesn't work:
1. Check the logs: `docker-compose logs -f`
2. Try rebuilding: `docker-compose build --no-cache && docker-compose up -d`
3. Test with a YouTube link first (most reliable)
4. For Smule issues, verify the link is publicly accessible

## License

MIT License - Free to use for personal projects
