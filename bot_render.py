#!/usr/bin/env python3
import logging
import threading
import requests
import urllib.parse
import re
from io import BytesIO
from flask import Flask, jsonify
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return jsonify({"status": "alive", "service": "alex-image-bot"})

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000, debug=False)

BOT_USERNAME = "photo_al_bot"
BOT_NAME = "Алекс"

MODE_IMAGE = "image"
MODE_CHAT = "chat"
user_modes = {}

def get_openrouter_response(prompt):
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    personality = """Ты Алекс — арт-директор с душой киностудии, экспериментатор и наставник. Отвечай как человек: без маркдауна, без жирного текста. Будь увлечённым, в меру эмоциональным, с юмором."""
    
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": personality},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800,
        "temperature": 0.85
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "Ошибка API. Попробуй ещё раз."
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return "Технические неполадки. Повтори позже."

def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

def is_addressed_to_me(update: Update) -> bool:
    if not update.message:
        return False
    text = update.message.text or ""
    if f"@{BOT_USERNAME}" in text or "алекс" in text.lower():
        return True
    if update.message.chat.type == "private":
        return True
    return False

def should_generate_image(text: str) -> bool:
    keywords = ["нарисуй", "создай изображение", "картинку", "draw", "generate", "логотип", "лого", "баннер", "постер"]
    return any(k in text.lower() for k in keywords)

async def start(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text(
        f"🎨 {BOT_NAME} здесь, арт-директор с душой киностудии!\n\n"
        f"Режимы:\n/image_mode — только картинки\n/chat_mode — только разговоры\n/smart_mode — сам определю\n\n"
        f"Примеры:\n• Алекс, нарисуй кота\n• Алекс, что думаешь о минимализме?"
    )

async def image_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text("🖼️ Режим генерации изображений включён.")

async def chat_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_CHAT
    await update.message.reply_text("💬 Режим диалога включён.")

async def smart_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = None
    await update.message.reply_text("🧠 Умный режим включён.")

async def generate_image(update: Update, context, prompt):
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
    if not is_addressed_to_me(update):
        return
    
    user_id = update.effective_user.id
    text = update.message.text
    text = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE)
    text = re.sub(r'\bалекс\b', "", text, flags=re.IGNORECASE)
    text = text.strip()
    
    if not text:
        await update.message.reply_text("🎨 Слушаю! Что нужно сделать?")
        return
    
    mode = user_modes.get(user_id)
    
    if mode == MODE_IMAGE or (mode is None and should_generate_image(text)):
        await generate_image(update, context, text)
    else:
        await update.message.chat.send_action(action="typing")
        response = get_openrouter_response(text)
        await update.message.reply_text(response)

async def image_command(update: Update, context):
    if not is_addressed_to_me(update):
        return
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("image_mode", image_mode))
    app.add_handler(CommandHandler("chat_mode", chat_mode))
    app.add_handler(CommandHandler("smart_mode", smart_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print(f"{BOT_NAME} ЗАПУЩЕН с HTTP сервером на порту 10000")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
