import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
from urllib.parse import urlparse
import re
from datetime import timedelta

# ================================================================
# WARNING: Only for initial testing - remove after confirmation!
BOT_TOKEN = "7608434233:AAHK1YuGDGcyqObwiPqBEgMHrfY5MZGAi10"
# ================================================================

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
SUPPORTED_DOMAINS = ['youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 'twitter.com', 'x.com', 'facebook.com']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video link to download!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = re.findall(r'https?://[^\s]+', update.message.text)[0]
        if not any(domain in urlparse(url).netloc.lower() for domain in SUPPORTED_DOMAINS):
            await update.message.reply_text("❌ Unsupported platform")
            return

        msg = await update.message.reply_text("⏳ Downloading...")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'format': 'best[filesize<50M]',
                'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
                'quiet': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                with open(file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption="Here's your video!",
                        supports_streaming=True
                    )
            
            await msg.delete()
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def set_webhook(application: Application):
    """Proper HTTPS webhook configuration"""
    if 'RENDER' in os.environ:
        webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"
        await application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        logger.info(f"Webhook set to: {webhook_url}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Configure webhook
    if 'RENDER' in os.environ:
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 8443)),
            webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}",
            drop_pending_updates=True
        )
    else:
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
