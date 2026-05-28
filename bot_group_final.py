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
BOT_NAME = "Алекс"

conversation_mode = False  # Режим диалога между ботами

def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

def is_direct_mention(update: Update) -> bool:
    """Проверяет, что сообщение адресовано именно этому боту"""
    if not update.message:
        return False
    
    message = update.message
    text = message.text or ""
    
    # Прямое упоминание через @username
    if f"@{BOT_USERNAME}" in text:
        return True
    
    # Ответ на сообщение бота
    if message.reply_to_message:
        if message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot:
            if message.reply_to_message.from_user.username == BOT_USERNAME:
                return True
    
    # Личный чат
    if message.chat.type == "private":
        return True
    
    return False

def is_bot_addressed_to_me(update: Update) -> bool:
    """Проверяет, обращается ли другой бот к этому боту"""
    if not update.message:
        return False
    
    text = update.message.text or ""
    reply_to = update.message.reply_to_message
    
    # Если другой бот написал и упомянул меня
    if reply_to and reply_to.from_user and reply_to.from_user.is_bot:
        if f"@{BOT_USERNAME}" in text:
            return True
    
    return False

async def start(update: Update, context):
    if not is_direct_mention(update):
        return
    await update.message.reply_text(
        f"🎨 {BOT_NAME} здесь!\n\n"
        f"Упомяните меня @{BOT_USERNAME}, чтобы я создал изображение.\n"
        f"Пример: @{BOT_USERNAME} кот в космосе\n\n"
        f"Команды:\n"
        f"/talk_on — включить режим диалога с другими ботами\n"
        f"/talk_off — выключить режим диалога"
    )

async def talk_on(update: Update, context):
    global conversation_mode
    if not is_direct_mention(update):
        return
    conversation_mode = True
    await update.message.reply_text(f"🗣️ Режим диалога включён. Теперь я буду отвечать другим ботам.")

async def talk_off(update: Update, context):
    global conversation_mode
    if not is_direct_mention(update):
        return
    conversation_mode = False
    await update.message.reply_text(f"🔇 Режим диалога выключен. Я отвечаю только на прямые упоминания.")

async def generate_image(update: Update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_data = generate_image_bytes(prompt)
    if img_data:
        await status_msg.delete()
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"✅ {prompt[:150]}")
    else:
        await status_msg.edit_text("❌ Не удалось создать изображение")

async def handle_message(update: Update, context):
    global conversation_mode
    
    if not update.message or not update.message.text:
        return
    
    # Если это личный чат или прямое упоминание
    if is_direct_mention(update):
        text = update.message.text
        text = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE)
        text = text.strip()
        
        if not text:
            return
        
        await generate_image(update, context, text)
        return
    
    # Если включён режим диалога и другой бот обращается ко мне
    if conversation_mode and is_bot_addressed_to_me(update):
        text = update.message.text
        text = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE)
        text = text.strip()
        
        if not text:
            return
        
        # Отвечаем на запрос другого бота
        await generate_image(update, context, text)
        return
    
    # Игнорируем все остальные сообщения в группе
    return

async def image_command(update: Update, context):
    if not is_direct_mention(update):
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
    app.add_handler(CommandHandler("talk_on", talk_on))
    app.add_handler(CommandHandler("talk_off", talk_off))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print(f"{BOT_NAME} ЗАПУЩЕН")
    print(f"Реагирует на: @{BOT_USERNAME}")
    print("Режим диалога: выключен (включите /talk_on)")
    print("=" * 50)
    
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
