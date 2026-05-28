#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

BOT_USERNAME = "photo_al_bot"
BOT_NAME = "Алекс"
BOT_NAME_LOWER = "алекс"

MODE_IMAGE = "image"
MODE_CHAT = "chat"
user_modes = {}

def get_openrouter_response(prompt):
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты Алекс, арт-директор и творческий собеседник. Отвечай как человек: без маркдауна, без жирного текста. Будь увлечённым, в меру эмоциональным, с юмором. Можешь рассуждать, шутить, задавать вопросы. Если спрашивают про изображения — описывай визуальные идеи. Если про творчество — вдохновляй."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
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
    
    message = update.message
    text = message.text or ""
    text_lower = text.lower()
    
    if f"@{BOT_USERNAME}" in text:
        return True
    
    if BOT_NAME_LOWER in text_lower:
        pattern = r'\b' + re.escape(BOT_NAME_LOWER) + r'\b'
        if re.search(pattern, text_lower):
            return True
    
    if message.reply_to_message:
        if message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot:
            if message.reply_to_message.from_user.username == BOT_USERNAME:
                return True
    
    if message.chat.type == "private":
        return True
    
    return False

def should_generate_image(text: str) -> bool:
    image_keywords = [
        "нарисуй", "создай изображение", "сгенерируй картинку", "покажи",
        "draw", "generate image", "make a picture", "нарисуйте",
        "изобрази", "картинку", "фото", "рисунок", "иллюстрацию"
    ]
    
    text_lower = text.lower()
    for keyword in image_keywords:
        if keyword in text_lower:
            return True
    return False

async def start(update: Update, context):
    if not is_addressed_to_me(update):
        return
    
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    
    await update.message.reply_text(
        f"🎨 {BOT_NAME} здесь!\n\n"
        f"Я умею:\n"
        f"• 🖼️ Генерировать изображения\n"
        f"• 💬 Отвечать на вопросы и рассуждать\n"
        f"• 📊 Создавать презентации\n\n"
        f"Как работать:\n"
        f"• {BOT_NAME}, нарисуй кота -> создам картинку\n"
        f"• {BOT_NAME}, что думаешь об ИИ? -> отвечу текстом\n"
        f"• /image_mode -> только картинки\n"
        f"• /chat_mode -> только текстовые ответы\n"
        f"• /smart_mode -> сам определю\n\n"
        f"Попробуй спросить: {BOT_NAME}, как тебе идея?"
    )

async def image_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text("🖼️ Режим: только генерация изображений")

async def chat_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_CHAT
    await update.message.reply_text("💬 Режим: только текстовые ответы и рассуждения")

async def smart_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = None
    await update.message.reply_text("🧠 Умный режим: сам определю, картинку или текст")

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
    text = re.sub(r'\b' + re.escape(BOT_NAME_LOWER) + r'\b', "", text, flags=re.IGNORECASE)
    text = text.strip()
    
    if not text:
        await update.message.reply_text(f"{BOT_NAME} слушает! Что хочешь?")
        return
    
    mode = user_modes.get(user_id)
    
    if mode == MODE_IMAGE:
        await generate_image(update, context, text)
    elif mode == MODE_CHAT:
        await update.message.chat.send_action(action="typing")
        response = get_openrouter_response(text)
        await update.message.reply_text(response)
    else:
        if should_generate_image(text):
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
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("image_mode", image_mode))
    app.add_handler(CommandHandler("chat_mode", chat_mode))
    app.add_handler(CommandHandler("smart_mode", smart_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print(f"{BOT_NAME} ЗАПУЩЕН (с текстовым режимом)")
    print(f"Реагирует на: @{BOT_USERNAME}, {BOT_NAME}")
    print("Режимы: /image_mode, /chat_mode, /smart_mode")
    print("=" * 50)
    
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
