"""
Spotify API клиент для поиска треков и получения ID.

Использует Client Credentials flow (не требует OAuth пользователя).
"""

import httpx
import base64
from typing import Optional, Dict, Any
from app.core.config import get_settings


class SpotifyClient:
    """Клиент для работы с Spotify Web API."""
    
    def __init__(self):
        """Инициализация клиента."""
        self.settings = get_settings()
        self.token: Optional[str] = None
        self.base_url = "https://api.spotify.com/v1"
        
    async def _get_access_token(self) -> str:
        """
        Получает access token через Client Credentials flow.
        
        Документация: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
        """
        client_id = self.settings.spotify_client_id
        client_secret = self.settings.spotify_client_secret
        
        if not client_id or not client_secret:
            raise ValueError(
                "Spotify credentials not configured. "
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env"
            )
        
        # Кодируем credentials в base64
        credentials = f"{client_id}:{client_secret}"
        credentials_b64 = base64.b64encode(credentials.encode()).decode()
        
        # Настраиваем прокси если есть
        proxy_url = None
        if self.settings.openai_proxy_host and self.settings.openai_proxy_type:
            proxy_type = self.settings.openai_proxy_type.lower()
            proxy_url = f"{proxy_type}://"
            
            if self.settings.openai_proxy_username and self.settings.openai_proxy_password:
                proxy_url += f"{self.settings.openai_proxy_username}:{self.settings.openai_proxy_password}@"
            
            proxy_url += f"{self.settings.openai_proxy_host}:{self.settings.openai_proxy_port}"
        
        # Запрос токена
        async with httpx.AsyncClient(proxies=proxy_url, timeout=30.0) as client:
            response = await client.post(
                "https://accounts.spotify.com/api/token",
                headers={
                    "Authorization": f"Basic {credentials_b64}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials"}
            )
            
            response.raise_for_status()
            data = response.json()
            return data["access_token"]
    
    async def _ensure_token(self):
        """Проверяет наличие токена и получает новый если нужно."""
        if not self.token:
            self.token = await self._get_access_token()
    
    async def search_track(
        self, 
        artist: str, 
        title: str, 
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Ищет трек на Spotify по артисту и названию.
        
        Args:
            artist: Имя артиста
            title: Название трека
            limit: Количество результатов (по умолчанию 1)
        
        Returns:
            Dict с данными первого найденного трека или None
            Структура: {
                "id": "spotify_track_id",
                "name": "Track Name",
                "artists": [{"name": "Artist"}],
                "url": "https://open.spotify.com/track/...",
                "preview_url": "https://..."  # может быть None
            }
        """
        await self._ensure_token()
        
        # Формируем поисковый запрос
        query = f"artist:{artist} track:{title}"
        
        # Настраиваем прокси
        proxy_url = None
        if self.settings.openai_proxy_host and self.settings.openai_proxy_type:
            proxy_type = self.settings.openai_proxy_type.lower()
            proxy_url = f"{proxy_type}://"
            
            if self.settings.openai_proxy_username and self.settings.openai_proxy_password:
                proxy_url += f"{self.settings.openai_proxy_username}:{self.settings.openai_proxy_password}@"
            
            proxy_url += f"{self.settings.openai_proxy_host}:{self.settings.openai_proxy_port}"
        
        # Выполняем поиск
        async with httpx.AsyncClient(proxies=proxy_url, timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/search",
                headers={"Authorization": f"Bearer {self.token}"},
                params={
                    "q": query,
                    "type": "track",
                    "limit": limit
                }
            )
            
            if response.status_code != 200:
                print(f"⚠️  Spotify API error: {response.status_code}")
                return None
            
            data = response.json()
            tracks = data.get("tracks", {}).get("items", [])
            
            if not tracks:
                return None
            
            track = tracks[0]
            return {
                "id": track["id"],
                "name": track["name"],
                "artists": [{"name": a["name"]} for a in track["artists"]],
                "url": track["external_urls"]["spotify"],
                "preview_url": track.get("preview_url")
            }
    
    async def get_track_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные трека по Spotify ID.
        
        Args:
            track_id: Spotify track ID
        
        Returns:
            Dict с данными трека или None
        """
        await self._ensure_token()
        
        proxy_url = None
        if self.settings.openai_proxy_host and self.settings.openai_proxy_type:
            proxy_type = self.settings.openai_proxy_type.lower()
            proxy_url = f"{proxy_type}://"
            
            if self.settings.openai_proxy_username and self.settings.openai_proxy_password:
                proxy_url += f"{self.settings.openai_proxy_username}:{self.settings.openai_proxy_password}@"
            
            proxy_url += f"{self.settings.openai_proxy_host}:{self.settings.openai_proxy_port}"
        
        async with httpx.AsyncClient(proxies=proxy_url, timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/tracks/{track_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code != 200:
                return None
            
            track = response.json()
            return {
                "id": track["id"],
                "name": track["name"],
                "artists": [{"name": a["name"]} for a in track["artists"]],
                "url": track["external_urls"]["spotify"],
                "preview_url": track.get("preview_url")
            }


# Singleton instance
_spotify_client: Optional[SpotifyClient] = None


def get_spotify_client() -> SpotifyClient:
    """Возвращает синглтон инстанс Spotify клиента."""
    global _spotify_client
    if _spotify_client is None:
        _spotify_client = SpotifyClient()
    return _spotify_client
