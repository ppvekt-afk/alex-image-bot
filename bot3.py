#!/usr/bin/env python3
import logging
import threading
import asyncio
from flask import Flask, jsonify
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from image_generator import ImageGenerator
from prompt_enhancer import PromptEnhancer
from handlers import start, help_command, styles_command, new_command, handle_message, memory_command, forget_command, history_command, stats_command, set_cache
from cache_skill import ImageCache
from utils import setup_logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return jsonify({"status": "alive"})

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

async def setup():
    cache = ImageCache()
    await cache.init_db()
    await set_cache(cache)
    
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    application.bot_data['image_generator'] = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    application.bot_data['prompt_enhancer'] = PromptEnhancer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("styles", styles_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("forget", forget_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application

def main():
    setup_logging(config.LOG_LEVEL)
    try:
        config.validate()
    except ValueError as e:
        print(f"Ошибка: {e}")
        return
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = loop.run_until_complete(setup())
    
    print("✅ Бот Алекс запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
