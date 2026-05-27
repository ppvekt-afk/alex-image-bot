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
