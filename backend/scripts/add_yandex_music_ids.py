"""
Скрипт для автоматического поиска и добавления Яндекс Музыка ID к песням.

Использует Яндекс Музыка API для поиска треков по названию и артисту.

Использование:
    python -m scripts.add_yandex_music_ids
    python -m scripts.add_yandex_music_ids --limit 10  # Обработать первые 10 песен
"""

import asyncio
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models import Song, ArtistProfile
from app.core.yandex_music_client import get_yandex_music_client
from sqlalchemy import select


async def add_yandex_music_ids(limit: int = None):
    """Добавляет Яндекс Музыка ID к песням в базе данных."""
    print("=" * 60)
    print("🎵 Добавление Яндекс Музыка ID к песням")
    print("=" * 60)
    
    yandex_client = get_yandex_music_client()
    
    try:
        yandex_client._ensure_client()
        print("\n✅ Яндекс Музыка API настроен и работает")
    except Exception as e:
        print("\nНастрой Яндекс Музыка API:")
        print("1. Установи библиотеку: pip install yandex-music")
        print("2. (Опционально) Получи токен на https://oauth.yandex.ru/")
        print("3. Добавь в .env:")
        print("   YANDEX_MUSIC_TOKEN=твой_токен")
        print("   (Без токена доступны только первые 30 сек треков)")
        print(f"\n❌ Ошибка подключения к Яндекс Музыка API: {e}")
        return
    
    async with AsyncSessionLocal() as db:
        # Находим песни без Яндекс Музыка ID
        query = select(Song).where(Song.yandex_music_id.is_(None))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        songs = result.scalars().all()
        
        if not songs:
            print("\n✅ Все песни уже имеют Яндекс Музыка ID")
            return
        
        print(f"\n📊 Найдено песен без Яндекс Музыка ID: {len(songs)}")
        print("=" * 60)
        
        added = 0
        not_found = 0
        errors = 0
        
        for idx, song in enumerate(songs, 1):
            # Получаем артиста
            artist_result = await db.execute(
                select(ArtistProfile).where(ArtistProfile.id == song.artist_id)
            )
            artist = artist_result.scalar_one()
            
            print(f"\n{idx}/{len(songs)}: {song.title} - {artist.name}")
            
            try:
                # Ищем трек на Яндекс Музыке
                track_data = await yandex_client.search_track(
                    artist=artist.name,
                    title=song.title
                )
                
                if track_data:
                    song.yandex_music_id = track_data["id"]
                    song.yandex_music_url = track_data["url"]
                    await db.commit()
                    
                    print(f"   ✅ Добавлено: {track_data['name']}")
                    print(f"      URL: {track_data['url']}")
                    added += 1
                else:
                    print(f"   ⚠️  Не найдено на Яндекс Музыке")
                    not_found += 1
                
                # Задержка чтобы не перегружать API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                errors += 1
                await db.rollback()
        
        print("\n" + "=" * 60)
        print("📊 Результаты:")
        print(f"   ✅ Добавлено Яндекс Музыка ID: {added}")
        print(f"   ⚠️  Не найдено на Яндекс Музыке: {not_found}")
        print(f"   ❌ Ошибок: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Добавить Яндекс Музыка ID к песням")
    parser.add_argument(
        "--limit",
        type=int,
        help="Обработать только первые N песен"
    )
    
    args = parser.parse_args()
    asyncio.run(add_yandex_music_ids(limit=args.limit))
