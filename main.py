import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import tempfile
import re

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration (Move to Render ENV Vars after testing)
BOT_TOKEN = os.getenv("BOT_TOKEN", "7608434233:AAHEowCeyqRiEtkqKhanm2otDnnOMJj0CU8")  # 🔴 Remove hardcoded token after testing
SUPPORTED_DOMAINS = ['youtube.com', 'instagram.com', 'tiktok.com']
PORT = int(os.getenv("PORT", 10000))  # Render uses 10000 by default

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video link to download!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = re.findall(r'https?://[^\s]+', update.message.text)[0]
        if not any(domain in url for domain in SUPPORTED_DOMAINS):
            await update.message.reply_text("❌ Unsupported platform")
            return

        msg = await update.message.reply_text("⏳ Downloading...")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {'outtmpl': f'{tmp_dir}/%(title)s.%(ext)s', 'quiet': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                with open(ydl.prepare_filename(info), 'rb') as f:
                    await update.message.reply_video(f)
        
        await msg.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    if 'RENDER' in os.environ:
        webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        logger.info(f"✅ Webhook active: {webhook_url}")
    else:
        app.run_polling()

if __name__ == '__main__':
    main()
