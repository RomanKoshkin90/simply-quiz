"""
Миграция для добавления полей spotify_id и spotify_url в таблицу songs.

Использование:
    python -m scripts.migrate_spotify_fields
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine


async def migrate():
    """Добавляет поля spotify_id и spotify_url в таблицу songs."""
    print("=" * 60)
    print("🔄 Миграция БД: добавление Spotify полей")
    print("=" * 60)
    
    async with engine.begin() as conn:
        try:
            # Проверяем существует ли таблица
            check_table = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'songs'
                );
            """
            result = await conn.execute(check_table)
            table_exists = result.scalar()
            
            if not table_exists:
                print("\n⚠️  Таблица songs не существует")
                print("   Запусти сначала создание таблиц:")
                print("   python -m scripts.process_songs")
                return
            
            # Проверяем существует ли поле spotify_id
            check_column = """
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'songs' AND column_name = 'spotify_id'
                );
            """
            result = await conn.execute(check_column)
            column_exists = result.scalar()
            
            if column_exists:
                print("\n✅ Поля spotify_id и spotify_url уже существуют")
                print("   Миграция не требуется")
                return
            
            # Добавляем поля
            print("\n📝 Добавляю поле spotify_id...")
            await conn.execute("""
                ALTER TABLE songs 
                ADD COLUMN IF NOT EXISTS spotify_id VARCHAR(50);
            """)
            
            print("📝 Добавляю поле spotify_url...")
            await conn.execute("""
                ALTER TABLE songs 
                ADD COLUMN IF NOT EXISTS spotify_url VARCHAR(255);
            """)
            
            # Создаем индекс для быстрого поиска по spotify_id
            print("📝 Создаю индекс для spotify_id...")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_songs_spotify_id 
                ON songs(spotify_id);
            """)
            
            print("\n✅ Миграция успешно завершена!")
            print("   Теперь можно запустить:")
            print("   - python -m scripts.process_songs  (для новых песен)")
            print("   - python -m scripts.add_spotify_ids  (для существующих песен)")
            
        except Exception as e:
            print(f"\n❌ Ошибка миграции: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate())
