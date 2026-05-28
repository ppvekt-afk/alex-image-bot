#!/usr/bin/env python3
import logging
import threading
import time
import os
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
@flask_app.route('/health')
def health():
    return jsonify({"status": "alive", "service": "alex-image-bot"})

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Запуск Flask health check сервера на порту {port}...")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 Алекс здесь!\n\n"
        "Я умею:\n"
        "• 🖼️ Генерировать изображения\n"
        "• 🎤 Распознавать голосовые сообщения\n\n"
        "Просто напиши 'нарисуй кота' или отправь голосовое сообщение!"
    )

async def generate_image(update: Update, context, prompt):
    import requests
    import urllib.parse
    from io import BytesIO
    
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200 and len(response.content) > 1000:
            await status_msg.delete()
            await update.message.reply_photo(photo=BytesIO(response.content), caption=f"✅ {prompt[:150]}")
        else:
            await status_msg.edit_text("❌ Не удалось создать изображение")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    if not text:
        return
    
    if any(k in text.lower() for k in ["нарисуй", "создай", "изобрази"]):
        await generate_image(update, context, text)
    else:
        await update.message.reply_text("Чтобы сгенерировать изображение, напиши 'нарисуй ...' или отправь голосовое!")

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(3)
    
    init_asr()
    tts_service.initialize()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("АЛЕКС ЗАПУЩЕН")
    print(f"Порт из переменной PORT: {os.environ.get('PORT', '10000')}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
