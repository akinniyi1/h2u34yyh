import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
from urllib.parse import urlparse
import re
from datetime import timedelta

# ==================================================================
# WARNING: This is for TEMPORARY TESTING ONLY!
# Remove the hardcoded token after testing and use environment variables
BOT_TOKEN = "7608434233:AAHK1YuGDGcyqObwiPqBEgMHrfY5MZGAi10"
# ==================================================================

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
RATE_LIMIT_PER_USER = timedelta(minutes=1)
USER_LAST_REQUEST = {}

SUPPORTED_DOMAINS = [
    'youtube.com', 'youtu.be',
    'instagram.com',
    'tiktok.com',
    'twitter.com', 'x.com',
    'facebook.com', 'fb.watch',
]

def is_supported_url(url):
    """Check if URL is from supported domain."""
    try:
        domain = urlparse(url).netloc.lower()
        return any(supported in domain for supported in SUPPORTED_DOMAINS)
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    await update.message.reply_text(
        "Hi! Send me video links from:\n"
        "- YouTube\n- Instagram\n- TikTok\n- Twitter/X\n- Facebook\n\n"
        "I'll download them for you!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process video download requests."""
    user_id = update.effective_user.id
    current_time = update.message.date
    
    # Rate limiting
    if user_id in USER_LAST_REQUEST:
        time_since_last = current_time - USER_LAST_REQUEST[user_id]
        if time_since_last < RATE_LIMIT_PER_USER:
            wait_time = (RATE_LIMIT_PER_USER - time_since_last).seconds // 60
            await update.message.reply_text(f"Please wait {wait_time} minute(s) before another request.")
            return
    
    USER_LAST_REQUEST[user_id] = current_time
    
    # Extract URL
    urls = re.findall(r'https?://[^\s]+', update.message.text)
    if not urls or not is_supported_url(urls[0]):
        await update.message.reply_text("❌ Unsupported URL. Send links from supported platforms.")
        return
    
    message = await update.message.reply_text("⏳ Downloading video...")
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'format': 'best[filesize<50M]',
                'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(urls[0], download=True)
                file_path = ydl.prepare_filename(info)
                
                with open(file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption="Here's your video!",
                        supports_streaming=True,
                    )
            
            await message.delete()
    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await message.edit_text(f"❌ Error: {str(e)}")

async def post_init(application: Application):
    """Run after bot initialization."""
    if 'RENDER' in os.environ:
        PORT = int(os.environ.get('PORT', 8443))
        webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
        
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=os.environ.get('WEBHOOK_SECRET', 'default-secret')
        )
        logger.info(f"Webhook configured: {webhook_url}")

def main():
    """Start the bot."""
    logger.info("Starting bot...")
    
    # Create Application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    if 'RENDER' in os.environ:
        PORT = int(os.environ.get('PORT', 8443))
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            secret_token=os.environ.get('WEBHOOK_SECRET', 'default-secret'),
            drop_pending_updates=True
        )
    else:
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
