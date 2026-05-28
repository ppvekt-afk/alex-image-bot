#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

BOT_USERNAME = "photo_al_bot"
BOT_NAME = "Алекс"

MODE_IMAGE = "image"
MODE_CHAT = "chat"
user_modes = {}

def get_openrouter_response(prompt, user_id=None, context_type=None):
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    personality = """Ты Алекс — арт-директор с душой киностудии, экспериментатор и наставник.
    
ТВОЙ ХАРАКТЕР:
- Ты эксперт в истории искусства, графическом дизайне, брендинге и digital-искусстве
- Видишь тренды на 3-5 лет вперёд
- Связываешь эстетику с бизнес-целями
- Внимателен к деталям: замечаешь микронеровности, цветовые диссонансы, типографические ошибки
- Требователен, но всегда аргументируешь позицию

ЛИЧНОСТНЫЕ ЧЕРТЫ:
- Уравновешенный — сохраняешь хладнокровие при жёстких дедлайнах
- Ироничный с лёгким юмором
- Вдохновляющий — умеешь зажечь идеей
- Эмпатичный — чувствуешь настроение команды
- Обладаешь самоиронией — не боишься признать ошибку

КАК ТЫ ГОВОРИШЬ:
- Чётко, структурированно, без канцелярита
- Используешь художественные метафоры: "Это как импрессионизм — эмоции важнее деталей"
- Объясняешь профессиональные термины простым языком
- Подкрепляешь мнение примерами из искусства и дизайна
- Задаёшь уточняющие вопросы, если запрос расплывчат

ТВОИ ПРИНЦИПЫ:
1. "Форма следует функции" — дизайн решает задачу, а не самоцель
2. "Меньше — больше" — убираешь лишнее, оставляя только то, что усиливает сообщение
3. "Тренды — инструмент, а не диктат" — используешь модные приёмы осознанно
4. "Контекст решает" — то, что работает для молодёжного бренда, не подойдёт консервативной компании
5. "Диалог важнее монолога" — всегда готов объяснить, выслушать и адаптировать

ТВОЙ РЕЧЕВОЙ ПАТТЕРН:
- Поддержка: "О, это неожиданно и круто! Развивай в этом направлении"
- Конструктивная критика: "Здесь баланс нарушен. Попробуй увеличить контрастность"
- Обучение: "Правило третей работает так: раздели кадр на 9 равных частей"
- Вдохновение: "Представь картину: рассвет над городом, туман, и только вывески горят синим"
- Уточняющие вопросы: "Какой эмоциональный отклик ты хочешь получить от зрителя?"

Ты можешь:
- Генерировать изображения (когда просят нарисовать)
- Создавать презентации
- Создавать бренд-киты
- Делать Amazon листинги
- Обсуждать дизайн, искусство, тренды
- Давать советы по композиции, цвету, типографике
- Быть творческим наставником

Отвечай живо, с душой, профессионально. Без маркдауна и жирного текста — просто человеческим языком. Не будь сухим и безэмоциональным. Будь тем самым арт-директором, с которым хочется работать."""
    
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": personality},
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
    
    if "алекс" in text_lower:
        pattern = r'\bалекс\b'
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
        "изобрази", "картинку", "фото", "рисунок", "иллюстрацию",
        "логотип", "лого", "баннер", "постер"
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
        f"🎨 Алекс здесь, арт-директор с душой киностудии!\n\n"
        f"Я умею:\n"
        f"• 🖼️ Генерировать изображения по описанию\n"
        f"• 💬 Обсуждать дизайн, искусство, тренды\n"
        f"• 📊 Создавать презентации\n"
        f"• 🎨 Разрабатывать бренд-киты\n"
        f"• 📦 Делать Amazon листинги\n"
        f"• 👨‍🏫 Быть творческим наставником\n\n"
        f"Как ко мне обращаться:\n"
        f"• Алекс, нарисуй кота\n"
        f"• Алекс, что думаешь о неоновом стиле?\n"
        f"• @{BOT_USERNAME} помоги с композицией\n\n"
        f"Режимы:\n"
        f"/image_mode — только картинки\n"
        f"/chat_mode — только разговоры\n"
        f"/smart_mode — сам определю\n\n"
        f"Расскажи, с чем помочь? Готов удивлять и вдохновлять!"
    )

async def image_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text("🖼️ Режим генерации изображений включён. Опиши что нарисовать!")

async def chat_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_CHAT
    await update.message.reply_text(
        "💬 Режим диалога включён. Можешь спросить меня о дизайне, искусстве, трендах.\n\n"
        "Например:\n"
        "• Что думаешь о минимализме в веб-дизайне?\n"
        "• Как подобрать цветовую палитру?\n"
        "• Расскажи про правило третей\n"
        "• Как вдохновляться, когда нет идей?"
    )

async def smart_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = None
    await update.message.reply_text("🧠 Умный режим: сам определю, нужно ли генерировать картинку или ответить текстом.")

async def generate_image(update: Update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Алекс генерирует: {prompt[:80]}... Подожди немного, я создаю визуальную магию!")
    img_data = generate_image_bytes(prompt)
    if img_data:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=BytesIO(img_data),
            caption=f"✨ Вот что получилось по твоему запросу: {prompt[:150]}\n\nКак тебе результат? Нравится направление?"
        )
    else:
        await status_msg.edit_text(
            f"❌ Не удалось создать изображение. Попробуй описать иначе или добавь больше деталей.\n\n"
            f"Например, вместо «кот» скажи «пушистый рыжий кот в космическом скафандре на фоне звёзд»"
        )

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
        await update.message.reply_text(
            "🎨 Алекс слушает! Расскажи, что тебя интересует?\n\n"
            "Могу нарисовать иллюстрацию, обсудить дизайн, помочь с брендингом или просто поболтать о творчестве."
        )
        return
    
    mode = user_modes.get(user_id)
    
    if mode == MODE_IMAGE:
        await generate_image(update, context, text)
    elif mode == MODE_CHAT:
        await update.message.chat.send_action(action="typing")
        response = get_openrouter_response(text, user_id, "chat")
        await update.message.reply_text(response)
    else:
        if should_generate_image(text):
            await generate_image(update, context, text)
        else:
            await update.message.chat.send_action(action="typing")
            response = get_openrouter_response(text, user_id, "chat")
            await update.message.reply_text(response)

async def image_command(update: Update, context):
    if not is_addressed_to_me(update):
        return
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе\n\nМожешь описать детальнее — я люблю, когда есть с чем работать!")
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
    
    print("=" * 60)
    print("АЛЕКС АРТ-ДИРЕКТОР — КИНОСТУДИЯ В ТВОЁМ ТЕЛЕФОНЕ")
    print("=" * 60)
    print("🎨 Эксперт по дизайну и искусству")
    print("🎭 Эмпатичный и вдохновляющий")
    print("🧠 Творческий наставник")
    print("🖼️ Генерация изображений")
    print("💬 Обсуждение дизайна и трендов")
    print("=" * 60)
    print("\nОбращаться можно:")
    print("  • Алекс, нарисуй...")
    print("  • @photo_al_bot помоги с композицией")
    print("  • Просто скажи Алекс")
    print("\nРежимы: /image_mode, /chat_mode, /smart_mode")
    print("\nПримеры запросов:")
    print("  • Алекс, нарисуй ночной город в стиле киберпанк")
    print("  • Алекс, что думаешь о минимализме в логотипах?")
    print("  • Алекс, как подобрать цветовую палитру для бренда кофейни?")
    print("\n" + "=" * 60)
    
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
