"""
Скрипт для автоматического создания слепков артистов из аудиофайлов.

Использование:
1. Положи вокалы артистов в папку backend/artist_vocals/
2. Название файла = название исполнителя (например: "Adele.mp3" -> "Adele")
3. Запусти: python -m scripts.process_artists

Скрипт автоматически:
- Определяет имя артиста из названия файла
- Обрабатывает аудио и извлекает характеристики
- Сохраняет в базу данных

Требования:
- PostgreSQL должен быть запущен
- .env должен быть настроен
- Все зависимости установлены
"""

import os
import sys
import uuid
import re
import asyncio
import argparse
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.audio_preprocessing import AudioPreprocessor
from app.core.pitch_extraction import PitchExtractor
from app.core.timbre_extraction import TimbreExtractor
from app.core.voice_embedding import embedding_generator
from app.db.database import AsyncSessionLocal, engine, Base
from app.db.models import ArtistProfile


# ============================================
# ДОПОЛНИТЕЛЬНАЯ КОНФИГУРАЦИЯ (опционально)
# Если нужно переопределить имя, жанр или тип голоса
# Формат: "имя_файла.mp3": { "name": "Имя", "genre": "жанр", "voice_type": "тип" }
# ============================================

ARTISTS_OVERRIDE = {
    # Примеры переопределений (если нужно)
    # "ed_sheeran.mp3": {
    #     "name": "Ed Sheeran",
    #     "genre": "pop",
    #     "voice_type": "tenor"
    # },
}


def extract_artist_name_from_filename(filename: str) -> str:
    """
    Извлекает имя артиста из названия файла.
    
    Примеры:
    - "Adele.mp3" -> "Adele"
    - "Ed Sheeran.mp3" -> "Ed Sheeran"
    - "Ария.mp3" -> "Ария"
    - "The Beatles.mp3" -> "The Beatles"
    """
    # Убираем расширение
    name = Path(filename).stem
    
    # Оставляем как есть (уже нормальное имя)
    return name


def detect_voice_type(min_pitch: float, max_pitch: float, median_pitch: float) -> str:
    """
    Автоматически определяет тип голоса на основе pitch диапазона.
    """
    # Классификация на основе типичных диапазонов
    if median_pitch < 150:
        if max_pitch < 350:
            return "bass"
        else:
            return "baritone"
    elif median_pitch < 250:
        if max_pitch < 520:
            return "tenor"
        else:
            return "tenor"  # Высокий тенор
    elif median_pitch < 350:
        if max_pitch < 700:
            return "alto"
        else:
            return "mezzo-soprano"
    else:
        if max_pitch < 880:
            return "mezzo-soprano"
        else:
            return "soprano"


def process_artist_audio(audio_path: str, skip_embedding: bool = False) -> dict:
    """
    Обрабатывает аудиофайл и извлекает характеристики голоса.
    
    Returns:
        dict с полями: min_pitch_hz, max_pitch_hz, median_pitch_hz, 
                      timbre_vector, voice_embedding
    """
    preprocessor = AudioPreprocessor()
    pitch_extractor = PitchExtractor()
    timbre_extractor = TimbreExtractor()
    
    # 1. Предобработка аудио
    print("      Загрузка и предобработка...")
    audio_data, sr, duration = preprocessor.preprocess(audio_path)
    
    # 2. Извлечение pitch (высоты голоса)
    print("      Извлечение pitch...")
    pitch_result = pitch_extractor.extract_pitch(audio_data, sr)
    pitch_analysis = pitch_extractor.analyze_pitch(pitch_result)
    
    # 3. Извлечение тембра
    print("      Извлечение тембра...")
    timbre_features = timbre_extractor.extract_features(audio_data, sr)
    timbre_key_features = timbre_extractor.extract_key_features(audio_data, sr)
    
    # 4. Генерация voice embedding (с OpenAI если настроено)
    voice_embedding = None
    if not skip_embedding:
        print("      Генерация voice embedding...")
        try:
            voice_embedding = embedding_generator.generate(
                audio_data, 
                sr, 
                pitch_analysis=pitch_analysis
            )
            voice_embedding = voice_embedding.tolist()  # Конвертируем в список для JSON
        except Exception as e:
            print(f"      ⚠️  Ошибка генерации embedding: {e}")
            print("      Продолжаю без embedding (можно добавить позже)")
            voice_embedding = None
    else:
        print("      ⏭️  Пропускаю генерацию embedding (--skip-embedding)")
    
    return {
        "min_pitch_hz": pitch_analysis.min_pitch_hz,
        "max_pitch_hz": pitch_analysis.max_pitch_hz,
        "median_pitch_hz": pitch_analysis.median_pitch_hz,
        "timbre_vector": timbre_key_features,
        "voice_embedding": voice_embedding,
        "detected_voice_type": pitch_analysis.detected_voice_type or detect_voice_type(
            pitch_analysis.min_pitch_hz,
            pitch_analysis.max_pitch_hz,
            pitch_analysis.median_pitch_hz
        ),
    }


async def main():
    parser = argparse.ArgumentParser(description='Обработка вокалов артистов')
    parser.add_argument(
        '--skip-embedding',
        action='store_true',
        help='Пропустить генерацию voice embedding (экономит токены OpenAI)'
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎤 Обработка вокалов артистов")
    if args.skip_embedding:
        print("⚠️  Режим: БЕЗ embedding (можно добавить позже)")
    print("=" * 60)
    
    # Проверяем папку с вокалами
    vocals_dir = Path(__file__).parent.parent / "artist_vocals"
    
    if not vocals_dir.exists():
        print(f"\n❌ Папка не найдена: {vocals_dir}")
        print("\n📁 Создай папку и положи туда вокалы артистов:")
        print(f"   mkdir {vocals_dir}")
        print("   # Скопируй файлы: adele.mp3, ed_sheeran.mp3, и т.д.")
        print("\n💡 Где взять вокал без музыки:")
        print("   - vocalremover.org (бесплатно)")
        print("   - lalal.ai")
        print("   - demucs (локально): pip install demucs")
        return
    
    # Получаем список файлов
    audio_files = list(vocals_dir.glob("*.mp3")) + \
                  list(vocals_dir.glob("*.wav")) + \
                  list(vocals_dir.glob("*.m4a")) + \
                  list(vocals_dir.glob("*.ogg"))
    
    if not audio_files:
        print(f"\n❌ В папке {vocals_dir} нет аудиофайлов!")
        print("   Поддерживаемые форматы: MP3, WAV, M4A, OGG")
        return
    
    print(f"\n📂 Найдено файлов: {len(audio_files)}")
    print(f"📂 Переопределений: {len(ARTISTS_OVERRIDE)}")
    
    # Создаем таблицы если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Подключаемся к базе
    async with AsyncSessionLocal() as db:
        processed = 0
        skipped = 0
        errors = 0
        
        for audio_file in audio_files:
            filename = audio_file.name
            
            # Определяем имя артиста из файла
            artist_name = extract_artist_name_from_filename(filename)
            
            # Проверяем, есть ли переопределение в конфиге
            override = ARTISTS_OVERRIDE.get(filename, {})
            artist_name = override.get("name", artist_name)
            genre = override.get("genre", "unknown")
            voice_type_override = override.get("voice_type")
            
            print(f"\n🎤 {artist_name} ({filename})")
            
            try:
                # Извлекаем характеристики (синхронная операция)
                features = process_artist_audio(str(audio_file), skip_embedding=args.skip_embedding)
                
                # Используем определенный тип голоса или из анализа
                voice_type = voice_type_override or features["detected_voice_type"]
                
                # Проверяем, есть ли уже такой артист в базе
                from sqlalchemy import select
                result = await db.execute(
                    select(ArtistProfile).where(ArtistProfile.name == artist_name)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Обновляем существующего
                    existing.genre = genre
                    existing.voice_type = voice_type
                    existing.min_pitch_hz = features["min_pitch_hz"]
                    existing.max_pitch_hz = features["max_pitch_hz"]
                    existing.median_pitch_hz = features["median_pitch_hz"]
                    existing.timbre_features = features["timbre_vector"]
                    existing.voice_embedding = features["voice_embedding"]
                    print(f"   ✅ Обновлён в базе")
                else:
                    # Создаём нового
                    artist = ArtistProfile(
                        name=artist_name,
                        genre=genre,
                        voice_type=voice_type,
                        min_pitch_hz=features["min_pitch_hz"],
                        max_pitch_hz=features["max_pitch_hz"],
                        median_pitch_hz=features["median_pitch_hz"],
                        timbre_features=features["timbre_vector"],
                        voice_embedding=features["voice_embedding"]
                    )
                    db.add(artist)
                    print(f"   ✅ Добавлен в базу")
                
                await db.commit()
                processed += 1
                
                # Показываем результат
                print(f"   📊 Диапазон: {features['min_pitch_hz']:.0f} - {features['max_pitch_hz']:.0f} Hz")
                print(f"   📊 Медиана: {features['median_pitch_hz']:.0f} Hz")
                print(f"   🎭 Тип голоса: {voice_type}")
                print(f"   🎵 Жанр: {genre}")
                
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
            print(f"⏭️  Пропущено: {skipped}")
        if errors:
            print(f"❌ Ошибок: {errors}")
        
        # Показываем всех артистов в базе
        result = await db.execute(select(ArtistProfile))
        all_artists = result.scalars().all()
        print(f"\n📚 Всего артистов в базе: {len(all_artists)}")
        for artist in all_artists:
            print(f"   • {artist.name} ({artist.voice_type}) — {artist.min_pitch_hz:.0f}-{artist.max_pitch_hz:.0f} Hz")


if __name__ == "__main__":
    asyncio.run(main())
