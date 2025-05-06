import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
import re
from urllib.parse import urlparse

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================================================
# TEMPORARY CONFIG (Replace with env vars after testing)
BOT_TOKEN = "7608434233:AAHEowCeyqRiEtkqKhanm2otDnnOMJj0CU8"
SUPPORTED_DOMAINS = ['youtube.com', 'youtu.be', 'instagram.com', 
                    'tiktok.com', 'twitter.com', 'x.com', 
                    'facebook.com', 'fb.watch']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
# ======================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📹 Send me a video link from:\n"
        "- YouTube\n- Instagram\n- TikTok\n- Twitter/X\n- Facebook"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = re.findall(r'https?://[^\s]+', update.message.text)[0]
        domain = urlparse(url).netloc.lower()
        
        if not any(supported in domain for supported in SUPPORTED_DOMAINS):
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
                        supports_streaming=True
                    )
            
            await msg.delete()
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    # Initialize bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Webhook configuration for Render
    if 'RENDER' in os.environ:
        webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"
        
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 10000)),  # Render uses 10000
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        logger.info(f"Webhook configured: {webhook_url}")
    else:
        application.run_polling()

if __name__ == '__main__':
    main()
