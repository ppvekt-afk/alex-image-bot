#!/usr/bin/env python3
import logging
import os
import sys
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging
from voice_handlers import handle_voice_message, init_asr
from tts_service import tts_service

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Инициализация голосовых сервисов
init_asr()
tts_service.initialize()

# --- Обработчики команд ---
async def start(update: Update, context):
    await update.message.reply_text("🎨 Алекс здесь!\n\nЯ умею:\n• 🖼️ Генерировать изображения\n• 🎤 Распознавать голосовые сообщения\n• 🔊 Отвечать голосом\n\nПросто отправь голосовое сообщение или напиши текст!")

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
        await update.message.reply_text("Чтобы сгенерировать изображение, напиши: 'Алекс, нарисуй ...'\n\nИли отправь голосовое сообщение!")

# Регистрация обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Flask Webhook ---
@flask_app.route('/')
def health():
    return jsonify({"status": "alive"})

@flask_app.route(f'/webhook/{config.TELEGRAM_BOT_TOKEN}', methods=['POST'])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        await dispatcher.process_update(update)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Method not allowed"}), 405

def main():
    # Установка webhook
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook/{config.TELEGRAM_BOT_TOKEN}"
    bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    # Запуск Flask
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()
