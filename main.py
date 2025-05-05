import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
from urllib.parse import urlparse
import re
from datetime import timedelta

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================================================================
# TEMPORARY HARDCODED TOKEN (REMOVE AFTER TESTING AND USE ENV VARIABLES)
BOT_TOKEN = "7608434233:AAHK1YuGDGcyqObwiPqBEgMHrfY5MZGAi10"
# =====================================================================

# Bot configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Telegram limit)
RATE_LIMIT_PER_USER = timedelta(minutes=1)
USER_LAST_REQUEST = {}

# Supported domains
SUPPORTED_DOMAINS = [
    'youtube.com', 'youtu.be',  # YouTube
    'instagram.com',  # Instagram
    'tiktok.com',  # TikTok
    'twitter.com', 'x.com',  # Twitter/X
    'facebook.com', 'fb.watch',  # Facebook
]

def is_supported_url(url):
    """Check if the URL is from a supported domain."""
    try:
        domain = urlparse(url).netloc.lower()
        return any(supported in domain for supported in SUPPORTED_DOMAINS)
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"Hi {user.first_name}! 👋\n\n"
        "I'm a video downloader bot. Just send me a link from:\n"
        "- YouTube\n- Instagram\n- TikTok\n- Twitter/X\n- Facebook\n\n"
        "I'll download and send you the video!"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when the command /help is issued."""
    help_text = (
        "How to use this bot:\n\n"
        "1. Send me a video link from supported platforms\n"
        "2. I'll download the video and send it back to you\n\n"
        "Supported platforms:\n"
        "- YouTube\n- Instagram\n- TikTok\n- Twitter/X\n- Facebook\n\n"
        "Note: Some videos might not be downloadable due to platform restrictions."
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages containing URLs."""
    user_id = update.effective_user.id
    current_time = update.message.date
    
    # Rate limiting check
    if user_id in USER_LAST_REQUEST:
        time_since_last = current_time - USER_LAST_REQUEST[user_id]
        if time_since_last < RATE_LIMIT_PER_USER:
            wait_time = (RATE_LIMIT_PER_USER - time_since_last).seconds // 60
            await update.message.reply_text(
                f"Please wait {wait_time} minute(s) before making another request."
            )
            return
    
    USER_LAST_REQUEST[user_id] = current_time
    
    # Extract URLs from message
    urls = re.findall(r'https?://[^\s]+', update.message.text)
    if not urls:
        await update.message.reply_text("Please send a valid video URL.")
        return
    
    url = urls[0]
    
    if not is_supported_url(url):
        await update.message.reply_text(
            "Sorry, this platform is not supported. "
            "Send /help to see supported platforms."
        )
        return
    
    # Inform user that download is starting
    message = await update.message.reply_text("⏳ Downloading video...")
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'format': 'best[filesize<50M]',
                'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'progress_hooks': [lambda d: progress_hook(d, update, context, message)],
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Could not extract video info")
                
                file_path = ydl.prepare_filename(info)
                if not os.path.exists(file_path):
                    raise Exception("Downloaded file not found")
                
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE:
                    raise Exception(
                        f"Video is too large ({file_size/1024/1024:.1f}MB). "
                        f"Max allowed is {MAX_FILE_SIZE/1024/1024:.1f}MB."
                    )
                
                # Send the video
                with open(file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption=f"Here's your video from {urlparse(url).netloc}",
                        supports_streaming=True,
                        filename=os.path.basename(file_path),
                    )
                
                await message.delete()
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        await message.edit_text(f"❌ Error: {str(e)}")

def progress_hook(d, update, context, message):
    """Update progress during download."""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', '?')
        eta = d.get('_eta_str', '?')
        
        text = (
            f"⏳ Downloading...\n"
            f"Progress: {percent}\n"
            f"Speed: {speed}\n"
            f"ETA: {eta}"
        )
        
        # Update message every 5% progress to avoid spamming
        if '_percent_str' in d:
            current_percent = float(d['_percent_str'].replace('%', ''))
            if current_percent % 5 < 0.5:  # Check for approximately every 5%
                try:
                    context.application.create_task(
                        message.edit_text(text)
                    )
                except:
                    pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "An unexpected error occurred. Please try again later."
        )

def main():
    """Start the bot."""
    print("🔍 Debug: Starting bot with token:", BOT_TOKEN[:5] + "...")  # Show partial token
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    if 'RENDER' in os.environ or 'RENDER_EXTERNAL_HOSTNAME' in os.environ:
        # Running on Render.com
        port = int(os.environ.get('PORT', 8443))
        hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
        
        print(f"🌐 Running on Render with hostname: {hostname}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"https://{hostname}/{BOT_TOKEN}"
        )
    else:
        # Fallback to polling (shouldn't happen on Render)
        print("🔄 Falling back to polling method")
        application.run_polling()

if __name__ == '__main__':
    main()
