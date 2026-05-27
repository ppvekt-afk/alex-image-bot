#!/bin/bash
cd ~/alex_art_bot
source venv/bin/activate

cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=FAKE_TOKEN
SD_API_URL=https://image.pollinations.ai/prompt
SD_API_KEY=
MAX_IMAGE_SIZE=1024
LOG_LEVEL=INFO
OPENROUTER_API_KEY=FAKE_TOKEN
OPENROUTER_MODEL=openai/gpt-oss-120b:free
EOF

cat > config.py << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    SD_API_URL = os.getenv("SD_API_URL", "https://image.pollinations.ai/prompt")
    SD_API_KEY = os.getenv("SD_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 1024))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
config = Config()
EOF

cat > utils.py << 'EOF'
import logging
import os
from datetime import datetime
def setup_logging(log_level: str = "INFO"):
    os.makedirs("logs", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    error_handler = logging.FileHandler("logs/errors.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(error_handler)
EOF

cat > cache_skill.py << 'EOF'
import hashlib
import aiosqlite
import logging
from typing import Optional, Dict, List
logger = logging.getLogger(__name__)
class ImageCache:
    def __init__(self, db_path: str = "alex_cache.db"):
        self.db_path = db_path
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS image_cache (prompt_hash TEXT PRIMARY KEY, user_prompt TEXT NOT NULL, enhanced_prompt TEXT, style TEXT, image_bytes BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id INTEGER, generation_count INTEGER DEFAULT 1)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON image_cache(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created ON image_cache(created_at DESC)")
            await db.commit()
        logger.info("Кэш инициализирован")
    def get_hash(self, prompt: str, style: str = "") -> str:
        return hashlib.md5(f"{prompt}|{style}".lower().encode()).hexdigest()
    async def get(self, prompt_hash: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT image_bytes, user_prompt, style, created_at FROM image_cache WHERE prompt_hash = ?", (prompt_hash,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {"image_bytes": row[0], "prompt": row[1], "style": row[2] or "стандартный", "created_at": row[3]}
        return None
    async def set(self, prompt_hash: str, user_prompt: str, enhanced_prompt: str, style: str, image_bytes: bytes, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT generation_count FROM image_cache WHERE prompt_hash = ?", (prompt_hash,)) as cursor:
                existing = await cursor.fetchone()
            if existing:
                await db.execute("UPDATE image_cache SET generation_count = generation_count + 1 WHERE prompt_hash = ?", (prompt_hash,))
            else:
                await db.execute("INSERT INTO image_cache VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 1)", (prompt_hash, user_prompt, enhanced_prompt, style, image_bytes, user_id))
            await db.commit()
    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_prompt, style, created_at, generation_count FROM image_cache WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
        return [{"prompt": r[0], "style": r[1] or "стандартный", "created_at": r[2], "count": r[3]} for r in rows]
    async def get_stats(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM image_cache") as c:
                total = (await c.fetchone())[0]
            async with db.execute("SELECT SUM(generation_count) FROM image_cache") as c:
                total_req = (await c.fetchone())[0] or 0
            async with db.execute("SELECT style, COUNT(*) FROM image_cache WHERE style IS NOT NULL GROUP BY style") as c:
                by_style = dict(await c.fetchall())
        return {"total_unique": total, "total_requests": total_req, "cache_hits": total_req - total, "by_style": by_style}
EOF

cat > image_generator.py << 'EOF'
import aiohttp, asyncio, logging, urllib.parse
from typing import Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
logger = logging.getLogger(__name__)
class ImageGenerator:
    def __init__(self, api_url: str, api_key: str = ""):
        self.api_url = api_url
        self.api_key = api_key
        self._session = None
    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
        return self._session
    @staticmethod
    def _is_retryable_error(e):
        return isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)) or (isinstance(e, aiohttp.ClientResponseError) and e.status == 429)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10), retry=retry_if_exception(_is_retryable_error), reraise=True)
    async def generate(self, prompt: str, style: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        style_prompts = {"реализм":"photorealistic","аниме":"anime","акварель":"watercolor","пиксель-арт":"pixel art","масло":"oil painting","карандаш":"pencil","фэнтези":"fantasy","киберпанк":"cyberpunk","космос":"space","природа":"nature","портрет":"portrait"}
        style_text = style_prompts.get(style, "")
        final_prompt = f"{prompt}, {style_text}, high quality" if style_text else f"{prompt}, high quality"
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_prompt)}?width=1024&height=1024&nologo=true"
        session = await self._get_session()
        async with session.get(url, timeout=60) as resp:
            if resp.status == 200:
                img = await resp.read()
                if len(img) > 1000:
                    return img, "✅"
                return None, "Пустое изображение"
            return None, f"Ошибка {resp.status}"
EOF

cat > prompt_enhancer.py << 'EOF'
import aiohttp, logging
from typing import Tuple
logger = logging.getLogger(__name__)
class PromptEnhancer:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self._session = None
        self.enabled = bool(api_key) and api_key != "FAKE_TOKEN"
    async def _get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    async def enhance(self, user_prompt: str, history=None) -> Tuple[str, str]:
        if not self.enabled:
            return user_prompt, "Без улучшения"
        session = await self._get_session()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": [{"role": "system", "content": "Улучши промпт для генерации изображения. Верни только улучшенный промпт на английском."}, {"role": "user", "content": user_prompt}], "temperature": 0.7, "max_tokens": 200}
        try:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip(), "Улучшен"
        except Exception as e:
            logger.error(f"Enhancer error: {e}")
        return user_prompt, "Без улучшения"
EOF

cat > memory_manager.py << 'EOF'
import json, logging
from typing import Dict, List
from datetime import datetime
from pathlib import Path
logger = logging.getLogger(__name__)
class MemoryManager:
    def __init__(self, memory_file: str = "user_memory.json"):
        self.memory_file = memory_file
        self.memory = json.load(open(memory_file)) if Path(memory_file).exists() else {}
    def _save(self):
        json.dump(self.memory, open(self.memory_file, 'w'), ensure_ascii=False, indent=2)
    def save_interaction(self, user_id: int, user_prompt: str, enhanced: str, style: str, feedback: str):
        uid = str(user_id)
        if uid not in self.memory:
            self.memory[uid] = {"interactions": [], "favorite_styles": {}, "total_requests": 0}
        u = self.memory[uid]
        u["total_requests"] += 1
        if style:
            u["favorite_styles"][style] = u["favorite_styles"].get(style, 0) + 1
        u["interactions"].append({"user_prompt": user_prompt, "enhanced": enhanced, "style": style, "feedback": feedback, "timestamp": datetime.now().isoformat()})
        if len(u["interactions"]) > 50:
            u["interactions"] = u["interactions"][-50:]
        self._save()
    def get_user_preferences(self, user_id: int, limit: int = 10) -> List[Dict]:
        return self.memory.get(str(user_id), {}).get("interactions", [])[-limit:]
    def get_learning_insights(self, user_id: int) -> Dict:
        u = self.memory.get(str(user_id), {})
        return {"total_requests": u.get("total_requests", 0), "favorite_styles": u.get("favorite_styles", {})}
EOF

cat > handlers.py << 'EOF'
import logging
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from image_generator import ImageGenerator
from prompt_enhancer import PromptEnhancer
from memory_manager import MemoryManager
from cache_skill import ImageCache
logger = logging.getLogger(__name__)
STYLES = {"реализм":"","аниме":"","акварель":"","пиксель-арт":"","масло":"","карандаш":"","фэнтези":"","киберпанк":"","космос":"","природа":"","портрет":""}
memory = MemoryManager()
cache = None
async def set_cache(c):
    global cache
    cache = c
async def start(update, context):
    await update.message.reply_text("🎨 Алекс! Команды: /start /help /styles /history /stats /new")
async def help_command(update, context):
    await update.message.reply_text("/history - история\n/stats - статистика\n/styles - стили")
async def styles_command(update, context):
    await update.message.reply_text("Стили: " + ", ".join(STYLES.keys()))
async def history_command(update, context):
    if not cache:
        await update.message.reply_text("Ошибка")
        return
    h = await cache.get_user_history(update.effective_user.id, 10)
    if not h:
        await update.message.reply_text("Нет истории")
        return
    text = "📖 История:\n" + "\n".join([f"{i}. {s['style']}: {s['prompt'][:40]}" for i,s in enumerate(h[:5],1)])
    await update.message.reply_text(text)
async def stats_command(update, context):
    if not cache:
        await update.message.reply_text("Ошибка")
        return
    s = await cache.get_stats()
    await update.message.reply_text(f"Уникальных: {s['total_unique']}\nСэкономлено: {s['cache_hits']}")
async def memory_command(update, context):
    i = memory.get_learning_insights(update.effective_user.id)
    await update.message.reply_text(f"Запросов: {i['total_requests']}")
async def forget_command(update, context):
    await update.message.reply_text("Забыл")
async def new_command(update, context):
    await update.message.reply_text("Опишите изображение")
async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    if len(text.split()) < 2:
        await update.message.reply_text("Подробнее, пожалуйста")
        return
    status = await update.message.reply_text("Обрабатываю...")
    style = next((s for s in STYLES if s in text.lower()), None)
    enhancer = context.bot_data.get('prompt_enhancer')
    generator = context.bot_data.get('image_generator')
    if not enhancer or not generator or not cache:
        await status.edit_text("Ошибка")
        return
    h = cache.get_hash(text, style or "")
    cached = await cache.get(h)
    if cached:
        await status.edit_text("⚡ Из кэша!")
        await update.message.reply_photo(InputFile(BytesIO(cached["image_bytes"]), "art.png"), caption=f"Кэш: {text[:50]}")
        await status.delete()
        return
    await status.edit_text("Улучшаю промпт...")
    enhanced, _ = await enhancer.enhance(text, None)
    await status.edit_text("Генерирую...")
    img, err = await generator.generate(enhanced, style)
    if img:
        await cache.set(h, text, enhanced, style or "", img, user_id)
        await status.delete()
        await update.message.reply_photo(InputFile(BytesIO(img), "art.png"), caption=f"✅ {text[:80]}")
        memory.save_interaction(user_id, text, enhanced, style, "positive")
    else:
        await status.edit_text(f"Ошибка: {err}")
EOF

cat > bot3.py << 'EOF'
#!/usr/bin/env python3
import logging, threading, asyncio
from flask import Flask, jsonify
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from image_generator import ImageGenerator
from prompt_enhancer import PromptEnhancer
from handlers import start, help_command, styles_command, new_command, handle_message, memory_command, forget_command, history_command, stats_command, set_cache
from cache_skill import ImageCache
from utils import setup_logging
logger = logging.getLogger(__name__)
app = Flask(__name__)
@app.route('/')
def health():
    return jsonify({"status": "alive"})
def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False)
async def setup():
    c = ImageCache()
    await c.init_db()
    await set_cache(c)
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.bot_data['image_generator'] = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    app.bot_data['prompt_enhancer'] = PromptEnhancer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    for cmd in ["start", "help", "styles", "new", "memory", "forget", "history", "stats"]:
        app.add_handler(CommandHandler(cmd, globals()[f"{cmd}_command"]))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
def main():
    setup_logging(config.LOG_LEVEL)
    try:
        config.validate()
    except ValueError as e:
        print(f"Ошибка: {e}")
        return
    threading.Thread(target=run_flask, daemon=True).start()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = loop.run_until_complete(setup())
    print("✅ Алекс запущен!")
    application.run_polling()
if __name__ == "__main__":
    main()
EOF

echo ""
echo "✅ Все файлы созданы!"
echo ""
echo "📝 Теперь отредактируйте .env и замените FAKE_TOKEN:"
echo "   nano .env"
echo ""
echo "🚀 Затем запустите бота:"
echo "   python bot3.py"
