"""
Скрипт для автоматического поиска и добавления Spotify ID к песням.

Использует Spotify Search API для поиска треков по названию и артисту.

Использование:
    python -m scripts.add_spotify_ids
    python -m scripts.add_spotify_ids --limit 10  # Обработать первые 10 песен
"""

import asyncio
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models import Song, ArtistProfile
from app.core.spotify_client import get_spotify_client
from sqlalchemy import select


async def add_spotify_ids(limit: int = None):
    """Добавляет Spotify ID к песням в базе данных."""
    print("=" * 60)
    print("🎵 Добавление Spotify ID к песням")
    print("=" * 60)
    
    spotify_client = get_spotify_client()
    
    # Проверяем конфигурацию
    try:
        await spotify_client._ensure_token()
        print("\n✅ Spotify API настроен и работает")
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nНастрой Spotify API:")
        print("1. Зайди на https://developer.spotify.com/dashboard")
        print("2. Создай приложение (любое название)")
        print("3. Скопируй Client ID и Client Secret")
        print("4. Добавь в backend/.env:")
        print("   SPOTIFY_CLIENT_ID=твой_client_id")
        print("   SPOTIFY_CLIENT_SECRET=твой_client_secret")
        return
    except Exception as e:
        print(f"\n❌ Ошибка подключения к Spotify API: {e}")
        print("\n⚠️  Проверь прокси настройки если используешь прокси")
        return
    
    updated = 0
    not_found = 0
    skipped = 0
    errors = 0
    
    async with AsyncSessionLocal() as db:
        # Находим песни без Spotify ID
        query = select(Song).where(Song.spotify_id.is_(None))
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        songs = result.scalars().all()
        
        if not songs:
            print("\n✅ Все песни уже имеют Spotify ID!")
            return
        
        print(f"\n📊 Песен без Spotify ID: {len(songs)}")
        
        if limit:
            print(f"🔍 Обрабатываем первые {limit}")
        
        for idx, song in enumerate(songs, 1):
            # Получаем артиста
            artist_result = await db.execute(
                select(ArtistProfile).where(ArtistProfile.id == song.artist_id)
            )
            artist = artist_result.scalar_one_or_none()
            
            if not artist:
                print(f"\n❌ {idx}/{len(songs)}: Артист не найден для песни '{song.title}'")
                errors += 1
                continue
            
            print(f"\n🎵 {idx}/{len(songs)}: {artist.name} - {song.title}")
            
            try:
                # Ищем трек на Spotify
                track_data = await spotify_client.search_track(
                    artist=artist.name,
                    title=song.title
                )
                
                if track_data:
                    song.spotify_id = track_data["id"]
                    song.spotify_url = track_data["url"]
                    
                    await db.commit()
                    
                    print(f"   ✅ Найдено: {track_data['name']}")
                    print(f"      ID: {track_data['id']}")
                    print(f"      URL: {track_data['url']}")
                    
                    if track_data.get("preview_url"):
                        print(f"      🎧 Превью: ДА")
                    else:
                        print(f"      ⚠️  Превью: НЕТ (будет только ссылка)")
                    
                    updated += 1
                else:
                    print(f"   ⚠️  Не найдено на Spotify")
                    not_found += 1
                
                # Небольшая задержка чтобы не перегружать API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                errors += 1
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ")
    print("=" * 60)
    print(f"✅ Добавлено Spotify ID: {updated}")
    print(f"⚠️  Не найдено на Spotify: {not_found}")
    print(f"❌ Ошибок: {errors}")
    print(f"📝 Всего обработано: {len(songs)}")
    
    if not_found > 0:
        print("\n💡 Для ненайденных треков:")
        print("   - Проверь правильность названий")
        print("   - Некоторые треки могут отсутствовать на Spotify")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Добавление Spotify ID")
    parser.add_argument(
        "--limit",
        type=int,
        help="Обработать только первые N песен (для тестирования)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(add_spotify_ids(limit=args.limit))
