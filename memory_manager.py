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
