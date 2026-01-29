"""
Скрипт для добавления песен в базу данных.

Использование:
1. Добавь артистов через process_artists.py
2. Настрой SONGS ниже
3. Запусти: python -m scripts.add_songs
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.models import Song, ArtistProfile


# ============================================
# КОНФИГУРАЦИЯ ПЕСЕН
# Добавь песни для каждого артиста
# Формат: "Имя артиста": [{ title, min_pitch, max_pitch, difficulty }]
# 
# difficulty: "easy" | "medium" | "hard"
# min/max_pitch: примерный диапазон песни в Hz
# ============================================

SONGS = {
    # Ed Sheeran
    "Ed Sheeran": [
        {"title": "Perfect", "min_pitch": 110, "max_pitch": 350, "difficulty": "easy"},
        {"title": "Shape of You", "min_pitch": 120, "max_pitch": 380, "difficulty": "medium"},
        {"title": "Thinking Out Loud", "min_pitch": 100, "max_pitch": 330, "difficulty": "easy"},
        {"title": "Photograph", "min_pitch": 115, "max_pitch": 340, "difficulty": "easy"},
        {"title": "Castle on the Hill", "min_pitch": 130, "max_pitch": 400, "difficulty": "medium"},
    ],
    
    # Adele
    "Adele": [
        {"title": "Hello", "min_pitch": 140, "max_pitch": 450, "difficulty": "medium"},
        {"title": "Someone Like You", "min_pitch": 130, "max_pitch": 400, "difficulty": "medium"},
        {"title": "Rolling in the Deep", "min_pitch": 150, "max_pitch": 500, "difficulty": "hard"},
        {"title": "Set Fire to the Rain", "min_pitch": 145, "max_pitch": 480, "difficulty": "hard"},
        {"title": "Easy On Me", "min_pitch": 120, "max_pitch": 380, "difficulty": "medium"},
    ],
    
    # Whitney Houston
    "Whitney Houston": [
        {"title": "I Will Always Love You", "min_pitch": 180, "max_pitch": 700, "difficulty": "hard"},
        {"title": "Greatest Love of All", "min_pitch": 170, "max_pitch": 550, "difficulty": "hard"},
        {"title": "I Wanna Dance with Somebody", "min_pitch": 200, "max_pitch": 600, "difficulty": "hard"},
        {"title": "How Will I Know", "min_pitch": 190, "max_pitch": 580, "difficulty": "hard"},
    ],
    
    # Ariana Grande
    "Ariana Grande": [
        {"title": "Thank U, Next", "min_pitch": 200, "max_pitch": 700, "difficulty": "hard"},
        {"title": "7 Rings", "min_pitch": 180, "max_pitch": 600, "difficulty": "medium"},
        {"title": "No Tears Left to Cry", "min_pitch": 220, "max_pitch": 750, "difficulty": "hard"},
        {"title": "Dangerous Woman", "min_pitch": 200, "max_pitch": 650, "difficulty": "hard"},
    ],
    
    # Bruno Mars
    "Bruno Mars": [
        {"title": "Just the Way You Are", "min_pitch": 130, "max_pitch": 420, "difficulty": "medium"},
        {"title": "Grenade", "min_pitch": 140, "max_pitch": 450, "difficulty": "medium"},
        {"title": "When I Was Your Man", "min_pitch": 120, "max_pitch": 380, "difficulty": "medium"},
        {"title": "Uptown Funk", "min_pitch": 150, "max_pitch": 400, "difficulty": "medium"},
        {"title": "Locked Out of Heaven", "min_pitch": 160, "max_pitch": 500, "difficulty": "hard"},
    ],
    
    # Beyoncé
    "Beyoncé": [
        {"title": "Halo", "min_pitch": 160, "max_pitch": 520, "difficulty": "medium"},
        {"title": "Single Ladies", "min_pitch": 180, "max_pitch": 550, "difficulty": "hard"},
        {"title": "Love on Top", "min_pitch": 200, "max_pitch": 700, "difficulty": "hard"},
        {"title": "If I Were a Boy", "min_pitch": 140, "max_pitch": 450, "difficulty": "medium"},
        {"title": "Crazy in Love", "min_pitch": 170, "max_pitch": 520, "difficulty": "hard"},
    ],
    
    # Lady Gaga
    "Lady Gaga": [
        {"title": "Shallow", "min_pitch": 150, "max_pitch": 550, "difficulty": "hard"},
        {"title": "Bad Romance", "min_pitch": 170, "max_pitch": 600, "difficulty": "hard"},
        {"title": "Poker Face", "min_pitch": 160, "max_pitch": 500, "difficulty": "medium"},
        {"title": "Born This Way", "min_pitch": 180, "max_pitch": 580, "difficulty": "hard"},
    ],
    
    # Frank Sinatra
    "Frank Sinatra": [
        {"title": "My Way", "min_pitch": 90, "max_pitch": 320, "difficulty": "medium"},
        {"title": "Fly Me to the Moon", "min_pitch": 100, "max_pitch": 350, "difficulty": "medium"},
        {"title": "New York, New York", "min_pitch": 95, "max_pitch": 340, "difficulty": "medium"},
        {"title": "The Way You Look Tonight", "min_pitch": 85, "max_pitch": 300, "difficulty": "easy"},
    ],
    
    # Freddie Mercury
    "Freddie Mercury": [
        {"title": "Bohemian Rhapsody", "min_pitch": 130, "max_pitch": 700, "difficulty": "hard"},
        {"title": "Somebody to Love", "min_pitch": 140, "max_pitch": 600, "difficulty": "hard"},
        {"title": "Don't Stop Me Now", "min_pitch": 150, "max_pitch": 650, "difficulty": "hard"},
        {"title": "We Are the Champions", "min_pitch": 120, "max_pitch": 500, "difficulty": "medium"},
        {"title": "Love of My Life", "min_pitch": 110, "max_pitch": 400, "difficulty": "medium"},
    ],
    
    # Michael Jackson
    "Michael Jackson": [
        {"title": "Billie Jean", "min_pitch": 140, "max_pitch": 450, "difficulty": "medium"},
        {"title": "Beat It", "min_pitch": 150, "max_pitch": 500, "difficulty": "hard"},
        {"title": "Thriller", "min_pitch": 130, "max_pitch": 420, "difficulty": "medium"},
        {"title": "Man in the Mirror", "min_pitch": 120, "max_pitch": 480, "difficulty": "hard"},
        {"title": "Human Nature", "min_pitch": 110, "max_pitch": 380, "difficulty": "easy"},
    ],
    
    # Celine Dion
    "Celine Dion": [
        {"title": "My Heart Will Go On", "min_pitch": 180, "max_pitch": 600, "difficulty": "hard"},
        {"title": "The Power of Love", "min_pitch": 170, "max_pitch": 580, "difficulty": "hard"},
        {"title": "All by Myself", "min_pitch": 160, "max_pitch": 700, "difficulty": "hard"},
        {"title": "Because You Loved Me", "min_pitch": 150, "max_pitch": 520, "difficulty": "medium"},
    ],
    
    # Русские артисты
    "Полина Гагарина": [
        {"title": "Кукушка", "min_pitch": 180, "max_pitch": 600, "difficulty": "medium"},
        {"title": "Миллион голосов", "min_pitch": 170, "max_pitch": 550, "difficulty": "medium"},
        {"title": "Спектакль окончен", "min_pitch": 160, "max_pitch": 500, "difficulty": "medium"},
        {"title": "Навек", "min_pitch": 150, "max_pitch": 480, "difficulty": "easy"},
    ],
    
    "Земфира": [
        {"title": "Искала", "min_pitch": 140, "max_pitch": 400, "difficulty": "medium"},
        {"title": "Хочешь?", "min_pitch": 130, "max_pitch": 380, "difficulty": "easy"},
        {"title": "Прости меня моя любовь", "min_pitch": 120, "max_pitch": 360, "difficulty": "easy"},
        {"title": "СПИД", "min_pitch": 135, "max_pitch": 420, "difficulty": "medium"},
    ],
    
    "Дима Билан": [
        {"title": "Believe", "min_pitch": 130, "max_pitch": 450, "difficulty": "medium"},
        {"title": "Never Let You Go", "min_pitch": 120, "max_pitch": 420, "difficulty": "medium"},
        {"title": "Задыхаюсь", "min_pitch": 140, "max_pitch": 480, "difficulty": "hard"},
        {"title": "Это была любовь", "min_pitch": 110, "max_pitch": 380, "difficulty": "easy"},
    ],
    
    "Григорий Лепс": [
        {"title": "Рюмка водки на столе", "min_pitch": 90, "max_pitch": 350, "difficulty": "medium"},
        {"title": "Самый лучший день", "min_pitch": 85, "max_pitch": 320, "difficulty": "easy"},
        {"title": "Я счастливый", "min_pitch": 95, "max_pitch": 360, "difficulty": "medium"},
        {"title": "Натали", "min_pitch": 80, "max_pitch": 300, "difficulty": "easy"},
    ],
}


def main():
    print("=" * 60)
    print("🎵 Добавление песен в базу")
    print("=" * 60)
    
    db = SessionLocal()
    added = 0
    skipped = 0
    artist_not_found = 0
    
    try:
        for artist_name, songs in SONGS.items():
            # Ищем артиста в базе
            artist = db.query(ArtistProfile).filter(
                ArtistProfile.name == artist_name
            ).first()
            
            if not artist:
                print(f"\n⚠️  Артист не найден: {artist_name}")
                print(f"   Сначала добавь артиста через process_artists.py")
                artist_not_found += 1
                continue
            
            print(f"\n🎤 {artist_name}")
            
            for song_data in songs:
                # Проверяем, есть ли уже такая песня
                existing = db.query(Song).filter(
                    Song.title == song_data["title"],
                    Song.artist_id == artist.id
                ).first()
                
                if existing:
                    print(f"   ⏭️  {song_data['title']} — уже есть")
                    skipped += 1
                    continue
                
                # Создаём песню
                song = Song(
                    id=str(uuid.uuid4()),
                    title=song_data["title"],
                    artist_id=artist.id,
                    min_pitch_hz=song_data["min_pitch"],
                    max_pitch_hz=song_data["max_pitch"],
                    difficulty=song_data["difficulty"]
                )
                
                db.add(song)
                added += 1
                
                difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                print(f"   ✅ {song_data['title']} {difficulty_emoji.get(song_data['difficulty'], '')}")
        
        db.commit()
        
        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ")
        print("=" * 60)
        print(f"✅ Добавлено песен: {added}")
        if skipped:
            print(f"⏭️  Пропущено (уже есть): {skipped}")
        if artist_not_found:
            print(f"⚠️  Артистов не найдено: {artist_not_found}")
        
        # Общая статистика
        total_songs = db.query(Song).count()
        total_artists = db.query(ArtistProfile).count()
        print(f"\n📚 Всего в базе:")
        print(f"   • Артистов: {total_artists}")
        print(f"   • Песен: {total_songs}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
