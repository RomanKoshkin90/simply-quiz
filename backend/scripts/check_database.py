"""
Скрипт для быстрой проверки состояния базы данных.

Запуск:
    python -m scripts.check_database
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db, engine
from app.db.models import ArtistProfile, Song, VoiceAnalysisResult
from sqlalchemy import select, func
from app.config import settings


async def check_database():
    """Проверяет состояние базы данных и выводит статистику."""
    print("=" * 70)
    print("🔍 Проверка базы данных Edinorok")
    print("=" * 70)
    
    # Показываем параметры подключения (без пароля)
    db_url = settings.database_url
    if "@" in db_url:
        # Скрываем пароль
        parts = db_url.split("@")
        if ":" in parts[0]:
            user_part = parts[0].split(":")[0].split("//")[-1]
            host_part = parts[1]
            safe_url = f"postgresql://{user_part}:***@{host_part}"
        else:
            safe_url = db_url
    else:
        safe_url = db_url
    
    print(f"\n📊 Параметры подключения:")
    print(f"   {safe_url}")
    print()
    
    try:
        # Подключаемся к БД
        async for session in get_db():
            print("✅ Подключение к базе данных успешно!")
            print()
            
            # 1. Проверка артистов
            print("👤 АРТИСТЫ:")
            print("-" * 70)
            
            artists_count = await session.execute(select(func.count(ArtistProfile.id)))
            total_artists = artists_count.scalar()
            print(f"   Всего артистов: {total_artists}")
            
            if total_artists > 0:
                # Артисты с embeddings
                artists_with_emb = await session.execute(
                    select(func.count(ArtistProfile.id))
                    .where(ArtistProfile.voice_embedding.isnot(None))
                )
                with_embedding = artists_with_emb.scalar()
                print(f"   С embeddings: {with_embedding} ({with_embedding*100//total_artists if total_artists > 0 else 0}%)")
                
                # Артисты с тембром
                artists_with_timbre = await session.execute(
                    select(func.count(ArtistProfile.id))
                    .where(ArtistProfile.timbre_features.isnot(None))
                )
                with_timbre = artists_with_timbre.scalar()
                print(f"   С тембром: {with_timbre} ({with_timbre*100//total_artists if total_artists > 0 else 0}%)")
                
                # Полностью обработанные
                complete = await session.execute(
                    select(func.count(ArtistProfile.id))
                    .where(
                        ArtistProfile.voice_embedding.isnot(None),
                        ArtistProfile.timbre_features.isnot(None)
                    )
                )
                complete_count = complete.scalar()
                print(f"   Полностью обработано: {complete_count} ({complete_count*100//total_artists if total_artists > 0 else 0}%)")
                
                # Примеры артистов
                sample_artists = await session.execute(
                    select(ArtistProfile.name, ArtistProfile.genre, ArtistProfile.voice_type)
                    .limit(5)
                )
                print(f"\n   Примеры артистов:")
                for artist in sample_artists.scalars().all():
                    emb_status = "✅" if artist.voice_embedding else "❌"
                    print(f"   {emb_status} {artist.name} ({artist.genre or 'unknown'}, {artist.voice_type or 'unknown'})")
            else:
                print("   ⚠️  База данных пустая! Нужно обработать артистов.")
                print("   Запусти: python -m scripts.process_artists")
            
            print()
            
            # 2. Проверка песен
            print("🎵 ПЕСНИ:")
            print("-" * 70)
            
            songs_count = await session.execute(select(func.count(Song.id)))
            total_songs = songs_count.scalar()
            print(f"   Всего песен: {total_songs}")
            
            if total_songs > 0:
                # Песни с pitch данными
                songs_with_pitch = await session.execute(
                    select(func.count(Song.id))
                    .where(Song.min_pitch_hz.isnot(None))
                )
                with_pitch = songs_with_pitch.scalar()
                print(f"   С pitch данными: {with_pitch} ({with_pitch*100//total_songs if total_songs > 0 else 0}%)")
                
                # Песни с difficulty
                songs_with_diff = await session.execute(
                    select(func.count(Song.id))
                    .where(Song.difficulty.isnot(None))
                )
                with_diff = songs_with_diff.scalar()
                print(f"   С difficulty: {with_diff} ({with_diff*100//total_songs if total_songs > 0 else 0}%)")
                
                # Примеры песен
                sample_songs = await session.execute(
                    select(Song.title, Song.artist_id, Song.difficulty)
                    .limit(5)
                )
                print(f"\n   Примеры песен:")
                for song in sample_songs.scalars().all():
                    print(f"   • {song.title} (difficulty: {song.difficulty or 'N/A'})")
            else:
                print("   ⚠️  Песен нет! Нужно обработать песни.")
                print("   Запусти: python -m scripts.process_songs")
            
            print()
            
            # 3. Проверка результатов анализа
            print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
            print("-" * 70)
            
            results_count = await session.execute(select(func.count(VoiceAnalysisResult.id)))
            total_results = results_count.scalar()
            print(f"   Всего анализов: {total_results}")
            
            print()
            
            # 4. Итоговая оценка
            print("=" * 70)
            print("📋 ИТОГОВАЯ ОЦЕНКА:")
            print("=" * 70)
            
            issues = []
            
            if total_artists == 0:
                issues.append("❌ Нет артистов в базе данных")
            elif with_embedding == 0:
                issues.append("❌ У артистов нет embeddings (нужно запустить: python -m scripts.add_embeddings)")
            elif with_embedding < total_artists:
                issues.append(f"⚠️  Не все артисты имеют embeddings ({with_embedding}/{total_artists})")
            
            if total_songs == 0:
                issues.append("❌ Нет песен в базе данных")
            
            if not issues:
                print("✅ База данных в порядке! Все данные на месте.")
                print()
                print("🎯 Блоки 'Похожие артисты' и 'Похожие песни' должны работать!")
            else:
                print("⚠️  Обнаружены проблемы:")
                for issue in issues:
                    print(f"   {issue}")
                print()
                print("🔧 Рекомендуемые действия:")
                if total_artists == 0:
                    print("   1. python -m scripts.process_artists")
                if with_embedding == 0 or with_embedding < total_artists:
                    print("   2. python -m scripts.add_embeddings")
                if total_songs == 0:
                    print("   3. python -m scripts.process_songs")
            
            print()
            break
            
    except Exception as e:
        print(f"❌ Ошибка при подключении к базе данных:")
        print(f"   {str(e)}")
        print()
        print("🔧 Проверь:")
        print("   1. PostgreSQL запущен")
        print("   2. Параметры в backend/.env правильные")
        print("   3. База данных 'edinorok' существует")
        print("   4. Пользователь имеет права доступа")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_database())
