#!/usr/bin/env python3
import logging
import threading
import time
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging
from voice_handlers import handle_voice_message, init_asr
from tts_service import tts_service

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return jsonify({"status": "alive", "service": "alex-art-bot"})

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080, debug=False)

async def start(update: Update, context):
    await update.message.reply_text("🎨 Алекс здесь!\n\nОтправь голосовое сообщение или напиши 'нарисуй кота'")

async def generate_image(update: Update, context, prompt):
    import requests, urllib.parse
    from io import BytesIO
    status = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 1000:
            await status.delete()
            await update.message.reply_photo(photo=BytesIO(resp.content), caption=f"✅ {prompt[:150]}")
        else:
            await status.edit_text("❌ Ошибка")
    except Exception as e:
        await status.edit_text(f"❌ {e}")

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if not text:
        return
    if any(k in text.lower() for k in ["нарисуй", "создай", "изобрази"]):
        await generate_image(update, context, text)
    else:
        await update.message.reply_text("Напиши 'нарисуй кота' или отправь голосовое")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    init_asr()
    tts_service.initialize()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Алекс запущен на порту 8080")
    app.run_polling()

if __name__ == "__main__":
    main()
