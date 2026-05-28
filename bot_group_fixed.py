#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

BOT_USERNAME = "photo_al_bot"
BOT_ID = "8552364756"  # ID вашего бота Алекса

def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

def is_mentioned(update: Update) -> bool:
    if not update.message:
        return False
    
    message = update.message
    text = message.text or ""
    
    # ТОЛЬКО прямое упоминание @username
    if f"@{BOT_USERNAME}" in text:
        return True
    
    # Ответ на сообщение этого бота
    if message.reply_to_message:
        if message.reply_to_message.from_user and message.reply_to_message.from_user.id == int(BOT_ID):
            return True
    
    # Личный чат
    if message.chat.type == "private":
        return True
    
    return False

async def start(update: Update, context):
    if not is_mentioned(update):
        return
    await update.message.reply_text(
        "🎨 Алекс здесь!\n\n"
        "Упомяните меня @photo_al_bot, чтобы я создал изображение.\n"
        "Пример: @photo_al_bot кот в космосе"
    )

async def generate_image(update: Update, context, prompt):
    if not is_mentioned(update):
        return
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_data = generate_image_bytes(prompt)
    if img_data:
        await status_msg.delete()
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"✅ {prompt[:150]}")
    else:
        await status_msg.edit_text("❌ Не удалось создать изображение")

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
    
    if not is_mentioned(update):
        return
    
    text = update.message.text
    # Убираем ТОЛЬКО своё упоминание
    text = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE)
    text = text.strip()
    
    if not text:
        return
    
    # Не реагируем на упоминания других ботов
    if "@photo_al_bot" not in update.message.text and "@masha_editor_bot" in update.message.text:
        return
    
    await generate_image(update, context, text)

async def image_command(update: Update, context):
    if not is_mentioned(update):
        return
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print(f"АЛЕКС ЗАПУЩЕН")
    print(f"Реагирует только на: @{BOT_USERNAME}")
    print("=" * 50)
    
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
