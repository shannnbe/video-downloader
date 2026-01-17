import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from downloader import download_video, is_valid_url, extract_url
from config import BOT_TOKEN, DOWNLOADS_DIR

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure downloads directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_message = """👋 Hi! I'm your Video Downloader Bot!

Send me a video link from:
🎤 Smule
📹 YouTube
📸 Instagram
🎵 TikTok
🐦 Twitter
👍 Facebook

I'll download it and send it back to you!

Just paste the link and I'll handle the rest 😊"""
    
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help is issued."""
    help_message = """🤖 How to use me:

1. Copy a video link from any supported platform
2. Paste it here
3. Wait a few seconds
4. Get your video!

✅ Supported platforms:
• Smule
• YouTube
• Instagram
• TikTok
• Twitter/X
• Facebook

⚠️ Note: Videos must be under 50MB"""
    
    await update.message.reply_text(help_message)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with URLs."""
    user_message = update.message.text
    user_id = update.effective_user.id
    
    logger.info(f"Received message from user {user_id}: {user_message[:50]}...")
    
    # Check if message contains a URL
    if not is_valid_url(user_message):
        await update.message.reply_text(
            "❌ Sorry, I couldn't recognize that link. Please send a valid video URL."
        )
        return
    
    # Extract URL from the message
    url = extract_url(user_message)
    logger.info(f"Extracted URL: {url}")
    
    # Send downloading message
    status_message = await update.message.reply_text("⏳ Downloading your video...")
    
    try:
        # Download the video
        video_path, error = await download_video(url, user_id)
        
        if error:
            # Handle specific error cases
            if "too large" in error.lower():
                await status_message.edit_text(
                    "❌ This video is too large (over 50MB). Try a shorter video."
                )
            elif "timeout" in error.lower():
                await status_message.edit_text(
                    "❌ Download took too long. The video might be too large or the connection is slow."
                )
            else:
                await status_message.edit_text(
                    "❌ Oops! I couldn't download this video. It might be private or unavailable."
                )
            logger.error(f"Download error for user {user_id}: {error}")
            return
        
        # Send the video file
        try:
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    supports_streaming=True
                )
            
            video_sent = True
            logger.info(f"Video sent successfully to user {user_id}")
        except Exception as e:
            video_sent = False
            logger.error(f"Failed to send video: {e}")
            await status_message.edit_text("❌ Failed to send video. Please try again.")
            return
        
        # Update status message to success (do this after video is confirmed sent)
        try:
            await status_message.edit_text("✅ Here's your video!")
        except Exception as e:
            # If editing fails, just log it - video was already sent successfully
            logger.warning(f"Could not edit status message: {e}")
        
        # Clean up the downloaded file
        try:
            os.remove(video_path)
            logger.info(f"Cleaned up video file: {video_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {video_path}: {e}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        try:
            await status_message.edit_text(
                "❌ Something went wrong. Please try again later."
            )
        except:
            # If we can't even edit the message, just pass
            pass


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
