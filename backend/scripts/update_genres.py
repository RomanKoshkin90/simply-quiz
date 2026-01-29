"""
Скрипт для обновления жанров артистов.

Можно:
1. Установить жанры вручную
2. Использовать Spotify API для автоопределения
3. Извлечь из метаданных MP3 файлов

Использование:
    python -m scripts.update_genres
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.db.models import ArtistProfile
from sqlalchemy import select


# Ручной словарь жанров (на основе известных артистов)
ARTIST_GENRES = {
    "Adele": "pop",
    "Ed Sheeran": "pop",
    "Bruno Mars": "pop",
    "Lady Gaga": "pop",
    "Katy Perry": "pop",
    "Rihanna": "pop",
    "Billie Eilish": "pop",
    "Shawn Mendes": "pop",
    "Sam Smith": "pop",
    "Ariana Grande": "pop",
    
    "Queen": "rock",
    "The Beatles": "rock",
    "Pink Floyd": "rock",
    "Led Zeppelin": "rock",
    "AC/DC": "rock",
    "Guns N' Roses": "rock",
    "Metallica": "metal",
    "Nirvana": "rock",
    "Red Hot Chili Peppers": "rock",
    "Foo Fighters": "rock",
    "Green Day": "punk",
    "Linkin Park": "rock",
    "System of a Down": "metal",
    "Slipknot": "metal",
    "Rammstein": "metal",
    "Arctic Monkeys": "indie",
    "The Killers": "rock",
    "Coldplay": "rock",
    "Muse": "rock",
    "Oasis": "rock",
    "Radiohead": "rock",
    "Alice in Chains": "grunge",
    "Pearl Jam": "grunge",
    "Soundgarden": "grunge",
    
    "Michael Jackson": "pop",
    "Madonna": "pop",
    "Whitney Houston": "pop",
    "Beyoncé": "r&b",
    "Aretha Franklin": "soul",
    "Marvin Gaye": "soul",
    "Stevie Wonder": "soul",
    "Prince": "funk",
    "James Brown": "funk",
    
    "Frank Sinatra": "jazz",
    "Ella Fitzgerald": "jazz",
    "Louis Armstrong": "jazz",
    "Michael Bublé": "jazz",
    "Jamie Cullum": "jazz",
    
    "Johnny Cash": "country",
    "Dolly Parton": "country",
    "Willie Nelson": "country",
    
    "Elvis Presley": "rock",
    "Chuck Berry": "rock",
    "The Rolling Stones": "rock",
    "David Bowie": "rock",
    "Elton John": "pop",
    "George Michael": "pop",
    
    "Eminem": "hip-hop",
    "Jay-Z": "hip-hop",
    "Kanye West": "hip-hop",
    "Drake": "hip-hop",
    "Kendrick Lamar": "hip-hop",
    
    "Bob Marley": "reggae",
    
    "Daft Punk": "electronic",
    "The Prodigy": "electronic",
    "Moby": "electronic",
    
    # Русские артисты
    "Кино": "rock",
    "Агата Кристи": "rock",
    "Сплин": "rock",
    "Би-2": "rock",
    "Ария": "metal",
    "Люмен": "rock",
    "Мумий Тролль": "rock",
    "Земфира": "rock",
    "Ночные Снайперы": "rock",
    "Браво": "pop",
    "Город 312": "pop",
    "Елка": "pop",
    "Loboda": "pop",
    "А-Студио": "pop",
    "Cream Soda": "pop",
    "Три дня дождя": "pop",
    "Мураками": "indie",
}


async def update_genres():
    """Обновляет жанры артистов в базе данных."""
    print("=" * 60)
    print("🎭 Обновление жанров артистов")
    print("=" * 60)
    
    updated = 0
    not_found = 0
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ArtistProfile))
        artists = result.scalars().all()
        
        print(f"\n📊 Всего артистов в базе: {len(artists)}")
        
        for artist in artists:
            if artist.name in ARTIST_GENRES:
                new_genre = ARTIST_GENRES[artist.name]
                old_genre = artist.genre
                
                if old_genre != new_genre:
                    artist.genre = new_genre
                    print(f"✅ {artist.name}: {old_genre or 'unknown'} -> {new_genre}")
                    updated += 1
            else:
                if not artist.genre or artist.genre == "unknown":
                    print(f"⚠️  {artist.name}: жанр не найден в словаре")
                    not_found += 1
        
        await db.commit()
    
    print("\n" + "=" * 60)
    print("📊 ИТОГИ")
    print("=" * 60)
    print(f"✅ Обновлено: {updated}")
    print(f"⚠️  Не найдено в словаре: {not_found}")
    print(f"📝 Всего артистов: {len(artists)}")
    
    if not_found > 0:
        print("\n💡 Добавь недостающие жанры в словарь ARTIST_GENRES")
        print("   в файле scripts/update_genres.py")


if __name__ == "__main__":
    asyncio.run(update_genres())
