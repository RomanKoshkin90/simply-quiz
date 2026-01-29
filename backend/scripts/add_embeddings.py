"""
Скрипт для добавления voice embeddings к уже обработанным артистам.

Использование:
    python -m scripts.add_embeddings                    # Все артисты без embedding
    python -m scripts.add_embeddings --artist "Adele"    # Конкретный артист
    python -m scripts.add_embeddings --limit 10         # Первые 10 артистов
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.audio_preprocessing import AudioPreprocessor
from app.core.pitch_extraction import PitchExtractor
from app.core.voice_embedding import embedding_generator
from app.db.database import AsyncSessionLocal, engine, Base
from app.db.models import ArtistProfile
from sqlalchemy import select, or_, func, cast
from sqlalchemy.dialects.postgresql import JSONB


async def add_embeddings(artist_name: str = None, limit: int = None):
    """Добавляет embeddings к артистам."""
    print("=" * 60)
    print("🔧 Добавление voice embeddings к артистам")
    print("=" * 60)
    
    # Создаем таблицы если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        # Находим всех артистов (будем фильтровать на стороне Python)
        query = select(ArtistProfile)
        
        if artist_name:
            query = query.where(ArtistProfile.name == artist_name)
        
        result = await db.execute(query)
        all_artists = result.scalars().all()
        
        # Фильтруем артистов без реального embedding
        # Проверяем: NULL, пустой массив, или placeholder (max < 0.01)
        artists = []
        for artist in all_artists:
            emb = artist.voice_embedding
            if emb is None or len(emb) == 0:
                artists.append(artist)
            elif isinstance(emb, list) and len(emb) > 0:
                # Проверяем на placeholder: если макс значение < 0.01, это placeholder
                max_val = max(abs(x) for x in emb)
                if max_val < 0.01:
                    artists.append(artist)
        
        if limit:
            artists = artists[:limit]
        
        if not artists:
            print("\n✅ Все артисты уже имеют реальный embedding!")
            return
        
        print(f"\n📊 Найдено артистов без реального embedding: {len(artists)}")
        if len(all_artists) > len(artists):
            print(f"    (из {len(all_artists)} всего, {len(all_artists) - len(artists)} имеют реальный embedding)")
        
        # Проверяем папку с вокалами
        vocals_dir = Path(__file__).parent.parent / "artist_vocals"
        
        if not vocals_dir.exists():
            print(f"\n❌ Папка не найдена: {vocals_dir}")
            print("   Нужны исходные аудио файлы для генерации embedding")
            return
        
        processed = 0
        errors = 0
        skipped = 0
        
        for artist in artists:
            print(f"\n🎤 {artist.name}")
            
            # Ищем файл артиста
            audio_files = (
                list(vocals_dir.glob(f"{artist.name}.mp3")) +
                list(vocals_dir.glob(f"{artist.name}.wav")) +
                list(vocals_dir.glob(f"{artist.name}.m4a")) +
                list(vocals_dir.glob(f"{artist.name}.ogg"))
            )
            
            if not audio_files:
                print(f"   ⏭️  Файл не найден, пропускаю")
                skipped += 1
                continue
            
            audio_file = audio_files[0]
            print(f"   📁 Файл: {audio_file.name}")
            
            try:
                # Предобработка
                preprocessor = AudioPreprocessor()
                audio_data, sr, duration = preprocessor.preprocess(str(audio_file))
                
                # Извлечение pitch (нужно для embedding)
                pitch_extractor = PitchExtractor()
                pitch_result = pitch_extractor.extract_pitch(audio_data, sr)
                pitch_analysis = pitch_extractor.analyze_pitch(pitch_result)
                
                # Генерация embedding
                print("      Генерация voice embedding...")
                voice_embedding = embedding_generator.generate(
                    audio_data,
                    sr,
                    pitch_analysis=pitch_analysis
                )
                
                # Обновляем в базе
                artist.voice_embedding = voice_embedding.tolist()
                await db.commit()
                
                print(f"   ✅ Embedding добавлен ({len(voice_embedding)} размерность)")
                processed += 1
                
            except Exception as e:
                import traceback
                print(f"   ❌ Ошибка: {e}")
                print(f"   📋 Детали: {traceback.format_exc()}")
                errors += 1
                await db.rollback()
                continue
        
        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ")
        print("=" * 60)
        print(f"✅ Обработано: {processed}")
        if skipped:
            print(f"⏭️  Пропущено (нет файла): {skipped}")
        if errors:
            print(f"❌ Ошибок: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Добавление voice embeddings к артистам')
    parser.add_argument(
        '--artist',
        type=str,
        help='Имя конкретного артиста для обработки'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Ограничить количество обрабатываемых артистов'
    )
    args = parser.parse_args()
    
    asyncio.run(add_embeddings(artist_name=args.artist, limit=args.limit))
