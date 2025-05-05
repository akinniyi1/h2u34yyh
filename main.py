import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
from urllib.parse import urlparse
import re
from datetime import timedelta

# ========== 🔴 TEMPORARY HARDCODED TOKEN (REMOVE LATER!) ==========
BOT_TOKEN = "7608434233:AAHK1YuGDGcyqObwiPqBEgMHrfY5MZGAi10"
# ==================================================================

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Telegram limit)
RATE_LIMIT_PER_USER = timedelta(minutes=1)
USER_LAST_REQUEST = {}

SUPPORTED_DOMAINS = [
    'youtube.com', 'youtu.be',  # YouTube
    'instagram.com',  # Instagram
    'tiktok.com',  # TikTok
    'twitter.com', 'x.com',  # Twitter/X
    'facebook.com', 'fb.watch',  # Facebook
]

def is_supported_url(url):
    try:
        domain = urlparse(url).netloc.lower()
        return any(supported in domain for supported in SUPPORTED_DOMAINS)
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a video link from YouTube/Instagram/TikTok/Twitter/Facebook, "
        "and I'll download it for you!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    urls = re.findall(r'https?://[^\s]+', update.message.text)
    
    if not urls or not is_supported_url(urls[0]):
        await update.message.reply_text("❌ Unsupported URL. Send a link from YouTube/Instagram/TikTok/Twitter/Facebook.")
        return

    message = await update.message.reply_text("⏳ Downloading...")
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'format': 'best[filesize<50M]',
                'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s',
                'quiet': True,
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
        await message.edit_text(f"❌ Error: {str(e)}")

def main():
    print("🤖 Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook setup for Render
    if 'RENDER' in os.environ:
        PORT = int(os.environ.get('PORT', 8443))
        WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
        
        print(f"🌐 Webhook URL: {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
        )
    else:
        print("🔵 Using polling (local testing)")
        application.run_polling()

if __name__ == '__main__':
    main()
