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

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)

async def start(update, context):
    await update.message.reply_text(
        "🎨 *Алекс Арт-директор*\n\n"
        "Я умею:\n"
        "• 🖼️ Генерировать изображения по тексту\n"
        "• 📊 Создавать презентации\n\n"
        "*Команды:*\n"
        "/start - приветствие\n"
        "/help - помощь\n"
        "/image [описание] - сгенерировать картинку\n"
        "/ppt [тема] - создать презентацию\n\n"
        "*Примеры:*\n"
        "• кот в космосе\n"
        "• /image закат на море\n"
        "• презентация про ИИ",
        parse_mode="Markdown"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "🆘 *Помощь*\n\n"
        "🖼️ *Изображения:*\n"
        "Напишите любой текст - я сгенерирую картинку\n"
        "/image [описание] - альтернативный способ\n\n"
        "📊 *Презентации:*\n"
        "/ppt [тема] - создать презентацию\n"
        "презентация про [тема]\n\n"
        "✨ *Совет:* Чем подробнее описание, тем лучше результат!",
        parse_mode="Markdown"
    )

async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: *{prompt[:80]}*...", parse_mode="Markdown")
    
    img_bytes, error = await image_gen.generate(prompt, None)
    
    if img_bytes:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="art.png"),
            caption=f"✅ *Изображение готово*\n📝 Запрос: {prompt[:150]}",
            parse_mode="Markdown"
        )
        return True
    else:
        await status_msg.edit_text(f"❌ *Ошибка:* {error}\n\nПопробуйте изменить описание.", parse_mode="Markdown")
        return False

async def create_ppt(update, context, topic):
    status_msg = await update.message.reply_text(f"📊 Создаю презентацию: *{topic[:80]}*...", parse_mode="Markdown")
    
    filename = f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{topic}</title>
    <style>
        body {{ margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: 'Segoe UI', Arial, sans-serif; }}
        .slide {{ min-height: 100vh; display: flex; align-items: center; justify-content: center; flex-direction: column; text-align: center; color: white; padding: 40px; }}
        h1 {{ font-size: 48px; margin-bottom: 20px; }}
        p {{ font-size: 24px; line-height: 1.5; max-width: 800px; }}
        .slide:nth-child(even) {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .slide:nth-child(3) {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        button {{ position: fixed; bottom: 20px; right: 20px; padding: 10px 20px; background: #333; color: white; border: none; border-radius: 5px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="slide">
        <h1>📊 {topic}</h1>
        <p>Профессиональная презентация</p>
    </div>
    <div class="slide">
        <h1>🎯 Основные цели</h1>
        <p>• Достижение результатов<br>• Оптимизация процессов<br>• Инновационные решения</p>
    </div>
    <div class="slide">
        <h1>🚀 Следующие шаги</h1>
        <p>Анализ → План → Внедрение → Результат</p>
    </div>
    <button onclick="document.documentElement.requestFullscreen()">⛶ Fullscreen</button>
    <script>
        let slide = 0;
        const slides = document.querySelectorAll('.slide');
        function show(n) {{ slides.forEach(s => s.style.display = 'none'); slides[n].style.display = 'flex'; }}
        document.addEventListener('keydown', (e) => {{
            if(e.key === 'ArrowRight') {{ slide = (slide + 1) % slides.length; show(slide); }}
            if(e.key === 'ArrowLeft') {{ slide = (slide - 1 + slides.length) % slides.length; show(slide); }}
        }});
        show(0);
    </script>
</body>
</html>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=InputFile(f, filename=filename),
            caption=f"🎨 *Презентация: {topic}*\n💡 Откройте в браузере, используйте стрелки → ←",
            parse_mode="Markdown"
        )
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def image_command(update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("❌ Укажите описание после команды /image\n\nПример: `/image кот в космосе`", parse_mode="Markdown")
        return
    await generate_image(update, context, prompt)

async def ppt_command(update, context):
    topic = " ".join(context.args) if context.args else "Презентация"
    await create_ppt(update, context, topic)

async def handle_message(update, context):
    text = update.message.text.strip()
    
    if not text:
        return
    
    lower_text = text.lower()
    
    if lower_text.startswith("/image"):
        return
    
    if lower_text.startswith("/ppt"):
        return
    
    if "презентац" in lower_text:
        topic = re.sub(r'(презентация|создай|про|на тему)', '', lower_text).strip()
        if not topic:
            topic = "Презентация"
        await create_ppt(update, context, topic)
    else:
        await generate_image(update, context, text)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("ppt", ppt_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🎨 АЛЕКС АРТ-ДИРЕКТОР ЗАПУЩЕН")
    print("=" * 50)
    print("✅ Генерация изображений: активна")
    print("✅ Создание презентаций: активно")
    print("=" * 50)
    print("\nОтправьте боту в Telegram:")
    print("• 'кот в космосе' → сгенерирует изображение")
    print("• 'презентация про ИИ' → создаст презентацию")
    print("• /image закат → сгенерирует изображение")
    print("• /ppt нейросети → создаст презентацию")
    print("\n" + "=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()

from handlers import campaign_command, generate_campaign_command
