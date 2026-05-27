#!/usr/bin/env python3
import logging
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging
from image_generator import ImageGenerator
from campaign_skill import ImageCampaign

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
campaign = ImageCampaign()
active_campaigns = {}

async def start(update, context):
    await update.message.reply_text(
        "🎨 *Алекс Арт-директор*\n\n"
        "Я умею:\n"
        "• 🖼️ Генерировать изображения\n"
        "• 📊 Создавать презентации\n"
        "• 📢 Создавать рекламные кампании\n\n"
        "*Команды:*\n"
        "/start - приветствие\n"
        "/help - помощь\n"
        "/image [описание] - картинка\n"
        "/ppt [тема] - презентация\n"
        "/campaign - рекламная кампания\n"
        "/generate_campaign - создать изображения кампании\n\n"
        "*Пример кампании:*\n"
        "/campaign кофе | молодые профессионалы | 1:1 | 3",
        parse_mode="Markdown"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "🆘 *Помощь*\n\n"
        "📢 *Рекламная кампания:*\n"
        "/campaign продукт | аудитория | соотношение | количество\n"
        "/generate_campaign - создать изображения\n\n"
        "🖼️ *Изображения:*\n"
        "Напишите любой текст\n"
        "/image [описание]\n\n"
        "📊 *Презентации:*\n"
        "/ppt [тема]\n"
        "презентация про [тема]",
        parse_mode="Markdown"
    )

async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: *{prompt[:80]}*...", parse_mode="Markdown")
    img_bytes, error = await image_gen.generate(prompt, None)
    if img_bytes:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="art.png"),
            caption=f"✅ *Готово*\n📝 {prompt[:150]}",
            parse_mode="Markdown"
        )
        return True
    else:
        await status_msg.edit_text(f"❌ *Ошибка:* {error}", parse_mode="Markdown")
        return False

async def create_ppt(update, context, topic):
    status_msg = await update.message.reply_text(f"📊 Создаю презентацию: *{topic[:80]}*...", parse_mode="Markdown")
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
        await update.message.reply_document(document=InputFile(f, filename=filename), caption=f"🎨 *Презентация: {topic}*", parse_mode="Markdown")
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def image_command(update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("❌ Пример: /image кот в космосе", parse_mode="Markdown")
        return
    await generate_image(update, context, prompt)

async def ppt_command(update, context):
    topic = " ".join(context.args) if context.args else "Презентация"
    await create_ppt(update, context, topic)

async def campaign_command(update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(
            "📊 *Image Campaign*\n\nФормат: /campaign продукт | аудитория | соотношение | количество\n\nПример: /campaign кофе | молодые профессионалы | 1:1 | 3",
            parse_mode="Markdown"
        )
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("❌ Используйте: продукт | аудитория")
        return
    
    product = parts[0]
    audience = parts[1]
    aspect_ratio = parts[2] if len(parts) > 2 and parts[2] in ["1:1", "16:9", "9:16", "4:3"] else "1:1"
    count = min(max(int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 3, 1), 5)
    
    status_msg = await update.message.reply_text("📊 Создаю бриф кампании...")
    
    brief = campaign.create_brief(product, audience, aspect_ratio, count)
    prompts = campaign.generate_prompts(brief)
    campaign_file = campaign.save_campaign(brief, prompts)
    
    active_campaigns[update.effective_user.id] = {"brief": brief, "prompts": prompts, "file": campaign_file}
    
    output = campaign.format_output(brief, prompts)
    await status_msg.edit_text(output, parse_mode="Markdown")

async def generate_campaign_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_campaigns:
        await update.message.reply_text("❌ Сначала создайте кампанию: /campaign продукт | аудитория")
        return
    
    data = active_campaigns[user_id]
    prompts = data["prompts"]
    brief = data["brief"]
    
    status_msg = await update.message.reply_text(f"🎨 Генерирую {len(prompts)} изображений...")
    
    generated = []
    for i, p in enumerate(prompts, 1):
        await status_msg.edit_text(f"🎨 {i}/{len(prompts)}: {p['name']}...")
        img_bytes, error = await image_gen.generate(p["prompt"], None)
        if img_bytes:
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=f"{p['name'].replace(' ', '_')}.png"),
                caption=f"*{p['name']}*\n{p['prompt'][:80]}...",
                parse_mode="Markdown"
            )
            generated.append(p["name"])
    
    await status_msg.delete()
    await update.message.reply_text(f"✅ *Кампания завершена!*\n✅ Успешно: {len(generated)}/{len(prompts)}", parse_mode="Markdown")

async def handle_message(update, context):
    text = update.message.text.strip()
    if not text:
        return
    lower = text.lower()
    
    if text.startswith("/"):
        return
    
    if "презентац" in lower:
        topic = re.sub(r'(презентация|создай|про|на тему)', '', lower).strip()
        await create_ppt(update, context, topic or "Презентация")
    else:
        await generate_image(update, context, text)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("ppt", ppt_command))
    app.add_handler(CommandHandler("campaign", campaign_command))
    app.add_handler(CommandHandler("generate_campaign", generate_campaign_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🎨 АЛЕКС С НАВЫКОМ IMAGE CAMPAIGN")
    print("=" * 50)
    print("✅ Генерация изображений")
    print("✅ Презентации")
    print("✅ Рекламные кампании")
    print("=" * 50)
    print("\nКоманда для кампании:")
    print("/campaign кофе | молодые профессионалы | 1:1 | 3")
    print("/generate_campaign - создать изображения")
    print("\n" + "=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
