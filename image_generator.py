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
