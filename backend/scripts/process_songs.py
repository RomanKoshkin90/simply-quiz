"""
Скрипт для автоматической обработки песен из папки backend/songs/

Формат файлов: "Артист - НазваниеАртист.mp3"
Пример: "Adele - SkyfallAdele.mp3" -> Артист: "Adele", Песня: "Skyfall"

Скрипт:
1. Парсит название файла
2. Извлекает название артиста и песни
3. Убирает дубликат имени артиста
4. Анализирует аудио (pitch диапазон)
5. Связывает с артистом в базе
6. Сохраняет в таблицу songs

Использование:
    python -m scripts.process_songs
    python -m scripts.process_songs --artist "Adele"  # Только песни артиста
"""

import os
import sys
import re
import asyncio
import argparse
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.audio_preprocessing import AudioPreprocessor
from app.core.pitch_extraction import PitchExtractor
from app.core.yandex_music_client import get_yandex_music_client
from app.db.database import AsyncSessionLocal, engine, Base
from app.db.models import ArtistProfile, Song
from sqlalchemy import select


def parse_song_filename(filename: str) -> dict:
    """
    Парсит название файла и извлекает артиста и название песни.
    
    Форматы:
    - "Adele - SkyfallAdele.mp3" -> artist: "Adele", title: "Skyfall"
    - "ABBA - Dancing QueenABBA.mp3" -> artist: "ABBA", title: "Dancing Queen"
    - "Alice Merton - No RootsAlice Merton.mp3" -> artist: "Alice Merton", title: "No Roots"
    
    Returns:
        dict с полями: artist, title, original_filename
    """
    # Убираем расширение
    name = Path(filename).stem
    
    # Разделяем по " - "
    if " - " not in name:
        print(f"      ⚠️  Неверный формат файла: {filename}")
        return None
    
    parts = name.split(" - ", 1)
    if len(parts) != 2:
        print(f"      ⚠️  Не удалось разобрать: {filename}")
        return None
    
    artist_name = parts[0].strip()
    song_with_artist = parts[1].strip()
    
    # Убираем дубликат имени артиста в конце
    # Пробуем разные варианты
    song_title = song_with_artist
    
    # Простое удаление артиста с конца (case-insensitive)
    if song_with_artist.lower().endswith(artist_name.lower()):
        song_title = song_with_artist[:-len(artist_name)].strip()
    
    # Убираем множественных артистов через запятую (George Michael, Aretha Franklin)
    if ", " in song_with_artist:
        # Берем текст до запятой
        song_title = song_with_artist.split(",")[0].strip()
        # Убираем артиста если есть
        if song_title.lower().endswith(artist_name.lower()):
            song_title = song_title[:-len(artist_name)].strip()
    
    # Убираем лишние пробелы и скобки в конце
    song_title = re.sub(r'\s+', ' ', song_title).strip()
    
    return {
        "artist": artist_name,
        "title": song_title,
        "original_filename": filename
    }


async def process_song_audio(audio_path: str) -> dict:
    """
    Анализирует аудиофайл песни и извлекает характеристики.
    
    Returns:
        dict с полями: min_pitch_hz, max_pitch_hz, duration_seconds
    """
    preprocessor = AudioPreprocessor()
    pitch_extractor = PitchExtractor()
    
    try:
        # Предобработка аудио
        audio_data, sr, duration = preprocessor.preprocess(audio_path)
        
        # Извлечение pitch (высоты голоса)
        pitch_result = pitch_extractor.extract_pitch(audio_data, sr)
        pitch_analysis = pitch_extractor.analyze_pitch(pitch_result)
        
        return {
            "min_pitch_hz": pitch_analysis.min_pitch_hz,
            "max_pitch_hz": pitch_analysis.max_pitch_hz,
            "duration_seconds": int(duration)
        }
    except Exception as e:
        print(f"      ⚠️  Ошибка анализа аудио: {e}")
        return None


async def main(filter_artist: str = None):
    """Основная функция обработки."""
    print("=" * 60)
    print("🎵 Обработка песен")
    print("=" * 60)
    
    # Путь к папке с песнями
    songs_dir = Path("songs")
    if not songs_dir.exists():
        print(f"\n❌ Папка {songs_dir} не найдена!")
        print("   Создай папку backend/songs/ и положи туда MP3 файлы")
        return
    
    # Находим все MP3 файлы
    mp3_files = sorted(songs_dir.glob("*.mp3"))
    
    print(f"\n📂 Найдено файлов: {len(mp3_files)}")
    
    if filter_artist:
        print(f"🔍 Фильтр по артисту: {filter_artist}")
        mp3_files = [f for f in mp3_files if filter_artist.lower() in f.name.lower()]
        print(f"   Отфильтровано: {len(mp3_files)} файлов")
    
    if not mp3_files:
        print("\n❌ Нет файлов для обработки")
        return
    
    # Инициализация Яндекс Музыка клиента
    yandex_client = get_yandex_music_client()
    yandex_enabled = False
    
    try:
        yandex_client._ensure_client()
        yandex_enabled = True
        print("✅ Яндекс Музыка API подключен (будет искать ID автоматически)")
    except Exception as e:
        print(f"⚠️  Яндекс Музыка API не настроен: {e}")
        print("   Песни будут добавлены без Яндекс Музыка ID")
        print("   Чтобы настроить, добавь в .env (опционально):")
        print("   YANDEX_MUSIC_TOKEN=твой_токен")
        print("   (Без токена доступны только первые 30 сек треков)")
    
    # Создаем таблицы если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    processed = 0
    skipped = 0
    errors = 0
    
    async with AsyncSessionLocal() as db:
        for idx, mp3_file in enumerate(mp3_files, 1):
            try:
                print(f"\n🎵 {idx}/{len(mp3_files)}: {mp3_file.name}")

                # Парсим название
                parsed = parse_song_filename(mp3_file.name)
                if not parsed:
                    errors += 1
                    continue

                artist_name = parsed["artist"]
                song_title = parsed["title"]

                print(f"   🎤 Артист: {artist_name}")
                print(f"   🎶 Песня: {song_title}")

                # Ищем артиста в базе (берем первого если есть дубликаты)
                try:
                    result = await db.execute(
                        select(ArtistProfile).where(ArtistProfile.name == artist_name).limit(1)
                    )
                    artist = result.scalar_one_or_none()
                except Exception as e:
                    print(f"   ⚠️  Ошибка поиска артиста: {e}")
                    print(f"   ⏭️  Пропускаю и продолжаю...")
                    errors += 1
                    continue

                if not artist:
                    print(f"   ⚠️  Артист '{artist_name}' не найден в базе. Пропускаю.")
                    skipped += 1
                    continue

                # Проверяем есть ли уже эта песня
                try:
                    result = await db.execute(
                        select(Song).where(
                            Song.artist_id == artist.id,
                            Song.title == song_title
                        )
                    )
                    existing_song = result.scalar_one_or_none()

                    if existing_song:
                        print(f"   ⏭️  Песня уже есть в базе")
                        skipped += 1
                        continue
                except Exception as e:
                    print(f"   ⚠️  Ошибка проверки существующей песни: {e}")
                    print(f"   ⏭️  Пропускаю и продолжаю...")
                    errors += 1
                    continue

                # Анализируем аудио
                print(f"      Анализирую аудио...")
                audio_features = await process_song_audio(str(mp3_file))

                if not audio_features:
                    errors += 1
                    continue

                # Определяем сложность на основе диапазона
                pitch_range = audio_features["max_pitch_hz"] - audio_features["min_pitch_hz"]
                if pitch_range < 200:
                    difficulty = 1  # Легкая
                elif pitch_range < 400:
                    difficulty = 2  # Средняя
                elif pitch_range < 600:
                    difficulty = 3  # Выше среднего
                elif pitch_range < 800:
                    difficulty = 4  # Сложная
                else:
                    difficulty = 5  # Очень сложная

                # Ищем Яндекс Музыка ID если доступен
                yandex_music_id = None
                yandex_music_url = None

                if yandex_enabled:
                    try:
                        print(f"      Ищу на Яндекс Музыке...")
                        track_data = await yandex_client.search_track(
                            artist=artist_name,
                            title=song_title
                        )

                        if track_data:
                            yandex_music_id = track_data["id"]
                            yandex_music_url = track_data["url"]
                            print(f"      ✅ Найдено на Яндекс Музыке: {track_data['name']}")
                        else:
                            print(f"      ⚠️  Не найдено на Яндекс Музыке")

                        # Задержка чтобы не перегружать API
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"      ⚠️  Ошибка Яндекс Музыка API: {e}")

                # Создаем запись в БД
                try:
                    new_song = Song(
                        title=song_title,
                        artist_id=artist.id,
                        min_pitch_hz=audio_features["min_pitch_hz"],
                        max_pitch_hz=audio_features["max_pitch_hz"],
                        duration_seconds=audio_features["duration_seconds"],
                        difficulty=difficulty,
                        genre=artist.genre,  # Берем жанр артиста
                        yandex_music_id=yandex_music_id,
                        yandex_music_url=yandex_music_url
                    )

                    db.add(new_song)
                    await db.commit()

                    print(f"   ✅ Добавлена в базу")
                    print(f"      Диапазон: {audio_features['min_pitch_hz']:.0f} - {audio_features['max_pitch_hz']:.0f} Hz")
                    print(f"      Длительность: {audio_features['duration_seconds']} сек")
                    print(f"      Сложность: {difficulty}/5 {'⭐' * difficulty}")

                    processed += 1

                except Exception as e:
                    print(f"   ❌ Ошибка сохранения в БД: {e}")
                    print(f"   ⏭️  Откатываю изменения и продолжаю...")
                    await db.rollback()
                    errors += 1

            except Exception as e:
                print(f"   ❌ Непредвиденная ошибка: {e}")
                print(f"   ⏭️  Продолжаю обработку следующего файла...")
                errors += 1
                continue
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ")
    print("=" * 60)
    print(f"✅ Обработано: {processed}")
    print(f"⏭️  Пропущено: {skipped}")
    print(f"❌ Ошибок: {errors}")
    print(f"📝 Всего файлов: {len(mp3_files)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обработка песен")
    parser.add_argument(
        "--artist",
        type=str,
        help="Фильтр по имени артиста (обработать только песни этого артиста)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(filter_artist=args.artist))
