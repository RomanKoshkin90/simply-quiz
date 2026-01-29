"""
Миграция для замены Spotify полей на Яндекс Музыка поля в таблице songs.

Использование:
    python -m scripts.migrate_yandex_music_fields
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine
from sqlalchemy import text


async def migrate_yandex_music_fields():
    """Заменяет spotify_id и spotify_url на yandex_music_id и yandex_music_url."""
    
    print("🔄 Миграция БД: замена Spotify полей на Яндекс Музыка")
    print("=" * 60)
    
    async with engine.begin() as conn:
        try:
            # Проверяем существует ли поле yandex_music_id
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'songs' AND column_name = 'yandex_music_id'
            """)
            result = await conn.execute(check_query)
            exists = result.fetchone()
            
            if exists:
                print("\n✅ Поля yandex_music_id и yandex_music_url уже существуют")
                print("   Миграция не требуется")
                return
            
            print("\n📝 Добавляю поле yandex_music_id...")
            await conn.execute(text("""
                ALTER TABLE songs 
                ADD COLUMN IF NOT EXISTS yandex_music_id VARCHAR(100);
            """))
            
            print("📝 Добавляю поле yandex_music_url...")
            await conn.execute(text("""
                ALTER TABLE songs 
                ADD COLUMN IF NOT EXISTS yandex_music_url VARCHAR(500);
            """))
            
            # Создаем индекс для быстрого поиска по yandex_music_id
            print("📝 Создаю индекс для yandex_music_id...")
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_songs_yandex_music_id 
                ON songs(yandex_music_id);
            """))
            
            # Копируем данные из spotify полей если они есть (проверяем существование колонок)
            print("📝 Копирую данные из spotify полей (если есть)...")
            try:
                await conn.execute(text("""
                    UPDATE songs 
                    SET yandex_music_id = spotify_id,
                        yandex_music_url = spotify_url
                    WHERE spotify_id IS NOT NULL 
                      AND yandex_music_id IS NULL;
                """))
            except Exception as e:
                print(f"   ⚠️  Не удалось скопировать данные из spotify (возможно, колонки не существуют): {e}")
            
            print("\n✅ Миграция завершена успешно!")
            print("\n📋 Следующие шаги:")
            print("   - python -m scripts.process_songs  (для новых песен)")
            print("   - python -m scripts.add_yandex_music_ids  (для существующих песен)")
            
        except Exception as e:
            print(f"\n❌ Ошибка миграции: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate_yandex_music_fields())
