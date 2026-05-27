#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("🎨 Алекс готов! Отправьте /help")

async def help_command(update, context):
    await update.message.reply_text("Команды: /start, /help, /poster [тема]")

async def poster_command(update, context):
    topic = " ".join(context.args) if context.args else "creative work"
    await update.message.reply_text(f"📰 Создаю постер на тему: {topic}\n✅ Функция готова!")

async def handle_message(update, context):
    await update.message.reply_text("Используйте /poster [тема] для создания постера")

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("poster", poster_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен с увеличенным таймаутом!")
    app.run_polling()

if __name__ == "__main__":
    main()
