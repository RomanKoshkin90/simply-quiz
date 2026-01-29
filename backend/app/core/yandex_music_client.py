"""
Яндекс Музыка API клиент для поиска треков и получения ID.

Использует yandex-music библиотеку для работы с API.
"""

from typing import Optional, Dict, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class YandexMusicClient:
    """Клиент для работы с Яндекс Музыка API."""
    
    def __init__(self):
        """Инициализация клиента."""
        self.token: Optional[str] = settings.yandex_music_token
        self._client = None
        self._initialized = False
        
    def _init_client(self):
        """Инициализирует клиент Яндекс Музыки."""
        if self._initialized:
            return
            
        try:
            from yandex_music import Client
            
            # Инициализируем клиент (без токена для базового доступа)
            # Без токена доступны только первые 30 секунд треков
            if self.token:
                self._client = Client(self.token).init()
                logger.info("✅ Яндекс Музыка клиент инициализирован с токеном")
            else:
                self._client = Client().init()
                logger.info("✅ Яндекс Музыка клиент инициализирован без токена (ограниченный доступ)")
            
            self._initialized = True
            
        except ImportError:
            logger.error("❌ Библиотека yandex-music не установлена. Установи: pip install yandex-music")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Яндекс Музыка: {e}")
            raise
    
    def _ensure_client(self):
        """Проверяет наличие клиента и инициализирует если нужно."""
        if not self._initialized:
            self._init_client()
    
    async def search_track(
        self, 
        artist: str, 
        title: str, 
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Ищет трек на Яндекс Музыке по артисту и названию.
        
        Args:
            artist: Имя артиста
            title: Название трека
            limit: Количество результатов (по умолчанию 1)
        
        Returns:
            Dict с данными первого найденного трека или None
            Структура: {
                "id": "yandex_track_id",
                "name": "Track Name",
                "artists": [{"name": "Artist"}],
                "url": "https://music.yandex.ru/album/.../track/...",
                "preview_url": "https://..."  # может быть None
            }
        """
        self._ensure_client()
        
        try:
            import asyncio
            
            # Формируем поисковый запрос
            query = f"{artist} {title}"
            
            # Выполняем поиск в отдельном потоке (yandex-music синхронный)
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                None,
                lambda: self._client.search(query, type_='track', page=0, page_size=limit)
            )
            
            if not search_result or not search_result.tracks:
                return None
            
            # Берем первый результат
            track = search_result.tracks.results[0]
            
            # Получаем полную информацию о треке
            full_track = await loop.run_in_executor(
                None,
                lambda: track.fetch_track() if hasattr(track, 'fetch_track') else track
            )
            
            # Формируем URL трека
            # Формат: https://music.yandex.ru/album/{album_id}/track/{track_id}
            track_id = full_track.id
            album_id = full_track.albums[0].id if full_track.albums else None
            
            url = None
            if album_id and track_id:
                url = f"https://music.yandex.ru/album/{album_id}/track/{track_id}"
            
            return {
                "id": str(track_id),
                "name": full_track.title,
                "artists": [{"name": a.name} for a in full_track.artists],
                "url": url,
                "preview_url": None,  # Яндекс Музыка не предоставляет preview_url через API
            }
            
        except Exception as e:
            logger.error(f"⚠️  Ошибка поиска трека на Яндекс Музыке: {e}")
            return None
    
    async def get_track_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные трека по Яндекс Музыка ID.
        
        Args:
            track_id: Яндекс Музыка track ID (формат: "track_id:album_id")
        
        Returns:
            Dict с данными трека или None
        """
        self._ensure_client()
        
        try:
            import asyncio
            
            # Формат ID: "track_id:album_id" или просто "track_id"
            if ':' in track_id:
                track_id_parts = track_id.split(':')
                track_id_only = track_id_parts[0]
                album_id = track_id_parts[1] if len(track_id_parts) > 1 else None
            else:
                track_id_only = track_id
                album_id = None
            
            # Получаем трек в отдельном потоке
            loop = asyncio.get_event_loop()
            tracks = await loop.run_in_executor(
                None,
                lambda: self._client.tracks([track_id_only])
            )
            
            if not tracks or len(tracks) == 0:
                return None
            
            track = tracks[0]
            
            # Формируем URL
            url = None
            if album_id:
                url = f"https://music.yandex.ru/album/{album_id}/track/{track_id_only}"
            elif track.albums:
                url = f"https://music.yandex.ru/album/{track.albums[0].id}/track/{track_id_only}"
            
            return {
                "id": str(track.id),
                "name": track.title,
                "artists": [{"name": a.name} for a in track.artists],
                "url": url,
                "preview_url": None,
            }
            
        except Exception as e:
            logger.error(f"⚠️  Ошибка получения трека по ID: {e}")
            return None


# Singleton instance
_yandex_music_client: Optional[YandexMusicClient] = None


def get_yandex_music_client() -> YandexMusicClient:
    """Возвращает синглтон инстанс Яндекс Музыка клиента."""
    global _yandex_music_client
    if _yandex_music_client is None:
        _yandex_music_client = YandexMusicClient()
    return _yandex_music_client
