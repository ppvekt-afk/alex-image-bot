#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
import threading
from io import BytesIO
from datetime import datetime
from pathlib import Path
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "OK", 200

def run_flask():
    port = int(config.PORT) if hasattr(config, 'PORT') else 10000
    flask_app.run(host='0.0.0.0', port=port)

active_brand_kits = {}
active_amazon_listings = {}

def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 АЛЕКС АРТ-ДИРЕКТОР\n\n"
        "Команды:\n"
        "/image текст - создать картинку\n"
        "/ppt тема - презентация\n"
        "/brandkit название | индустрия\n"
        "/generate_brand_images\n"
        "/amazon название | категория | особенности\n"
        "/generate_amazon_listing\n\n"
        "Любой текст - создаст изображение"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "/image текст - изображение\n"
        "/ppt тема - презентация\n"
        "/brandkit название | индустрия\n"
        "/generate_brand_images\n"
        "/amazon название | категория | особенности\n"
        "/generate_amazon_listing"
    )

async def generate_image(update: Update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_data = generate_image_bytes(prompt)
    if img_data:
        await status_msg.delete()
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"✅ {prompt[:150]}")
        return True
    else:
        await status_msg.edit_text("❌ Не удалось создать изображение")
        return False

async def create_ppt(update: Update, context, topic):
    status_msg = await update.message.reply_text(f"📊 Создаю презентацию: {topic[:80]}...")
    filename = f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{topic}</title>
<style>
body {{ margin:0; background:linear-gradient(135deg,#667eea,#764ba2); font-family:Arial; }}
.slide {{ min-height:100vh; display:flex; align-items:center; justify-content:center; flex-direction:column; text-align:center; color:white; padding:20px; }}
h1 {{ font-size:48px; }}
p {{ font-size:24px; }}
</style>
</head>
<body>
<div class="slide"><h1>📊 {topic}</h1><p>Презентация</p></div>
</body>
</html>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(document=f, filename=filename, caption=f"📊 Презентация: {topic}")
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def image_command(update: Update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

async def ppt_command(update: Update, context):
    topic = " ".join(context.args) if context.args else "Презентация"
    await create_ppt(update, context, topic)

async def brandkit_command(update: Update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text("Формат: /brandkit название | индустрия\nПример: /brandkit Lumina | tech startup")
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Используйте: название | индустрия")
        return
    
    brand_name = parts[0]
    industry = parts[1]
    
    active_brand_kits[update.effective_user.id] = {"brand_name": brand_name, "industry": industry}
    
    await update.message.reply_text(f"✅ Бренд-кит создан!\nНазвание: {brand_name}\nИндустрия: {industry}\n\nОтправьте /generate_brand_images")

async def generate_brand_images_command(update: Update, context):
    user_id = update.effective_user.id
    if user_id not in active_brand_kits:
        await update.message.reply_text("Сначала создайте бренд-кит: /brandkit название | индустрия")
        return
    
    data = active_brand_kits[user_id]
    brand_name = data["brand_name"]
    industry = data["industry"]
    
    await update.message.reply_text(f"🎨 Создаю визуалы для бренда {brand_name}...")
    
    prompts = {
        "logo": f"Minimalist logo for '{brand_name}', {industry} brand, clean vector-style on white background",
        "moodboard": f"Brand moodboard for '{brand_name}', {industry}, show 5 color palette swatches",
        "pattern": f"Seamless brand pattern for '{brand_name}', {industry}, subtle and modern"
    }
    
    for name, prompt in prompts.items():
        img_data = generate_image_bytes(prompt)
        if img_data:
            await update.message.reply_photo(photo=BytesIO(img_data), caption=f"{name.upper()} для бренда {brand_name}")
    
    await update.message.reply_text(f"✅ Бренд-кит для {brand_name} готов!")

async def amazon_command(update: Update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text("Формат: /amazon название | категория | особенности | покупатель\nПример: /amazon Термокружка | Kitchen & Dining | герметичная | офисные работники")
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("Используйте: название | категория | особенности | покупатель")
        return
    
    product_name = parts[0]
    product_category = parts[1]
    key_features = parts[2]
    target_buyer = parts[3] if len(parts) > 3 else "general consumer"
    
    active_amazon_listings[update.effective_user.id] = {
        "product_name": product_name,
        "product_category": product_category,
        "key_features": key_features,
        "target_buyer": target_buyer
    }
    
    await update.message.reply_text(f"✅ Amazon листинг создан!\nПродукт: {product_name}\nКатегория: {product_category}\n\nОтправьте /generate_amazon_listing")

async def generate_amazon_listing_command(update: Update, context):
    user_id = update.effective_user.id
    if user_id not in active_amazon_listings:
        await update.message.reply_text("Сначала создайте Amazon листинг: /amazon название | категория | особенности")
        return
    
    data = active_amazon_listings[user_id]
    product_name = data["product_name"]
    product_category = data["product_category"]
    key_features = data["key_features"]
    target_buyer = data["target_buyer"]
    
    await update.message.reply_text(f"📦 Создаю 4 изображения для {product_name}...")
    
    features_text = ", ".join([f.strip() for f in key_features.split(",")][:3])
    
    prompts = {
        "hero": f"Professional Amazon main listing hero image of {product_name}. Pure white background, product centered, soft studio lighting",
        "lifestyle": f"Amazon lifestyle image of {product_name} being used by {target_buyer} in natural setting. {product_category} product in real-life context",
        "infographic": f"Amazon product infographic for {product_name}. Shows product with callout arrows highlighting: {features_text}. Clean white background",
        "detail": f"Extreme closeup macro product detail shot of {product_name}, focus on premium materials, studio lighting, white background"
    }
    
    for name, prompt in prompts.items():
        img_data = generate_image_bytes(prompt)
        if img_data:
            await update.message.reply_photo(photo=BytesIO(img_data), caption=f"{name.upper()} для {product_name}")
    
    await update.message.reply_text(f"✅ Amazon листинг для {product_name} готов!")

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    if not text or text.startswith("/"):
        return
    
    lower = text.lower()
    
    if "презентац" in lower:
        topic = re.sub(r'(презентация|создай|про|на тему)', '', lower).strip()
        await create_ppt(update, context, topic or "Презентация")
    else:
        await generate_image(update, context, text)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("ppt", ppt_command))
    app.add_handler(CommandHandler("brandkit", brandkit_command))
    app.add_handler(CommandHandler("generate_brand_images", generate_brand_images_command))
    app.add_handler(CommandHandler("amazon", amazon_command))
    app.add_handler(CommandHandler("generate_amazon_listing", generate_amazon_listing_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("АЛЕКС АРТ-ДИРЕКТОР ЗАПУЩЕН с HTTP-сервером на порту 10000")
    print("=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
