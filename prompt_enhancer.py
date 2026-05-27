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
