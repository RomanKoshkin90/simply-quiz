# 🎤 Edinorok - AI Voice Analyzer

Анализатор голоса с рекомендациями песен на основе AI.

---

## 🌟 Основные возможности

### ✨ Для пользователей
- **Live анализ голоса** - поёшь прямо в микрофон, получаешь результат
- **Загрузка аудио** - загружаешь файл с пением
- **Определение типа голоса** - Бас, Баритон, Тенор, Альт, Меццо-сопрано, Сопрано
- **Анализ диапазона** - минимальная/максимальная нота в русском формате (До, Ре, Ми...)
- **Тембр голоса** - яркость, стабильность, мощность, резонанс, динамика (с понятными объяснениями)
- **Похожие артисты** - находит 3 артиста с похожим голосом из базы 130+ исполнителей
- **Рекомендованные песни** - подбирает песни под твой диапазон
- **Spotify плееры** - слушай 30-сек превью прямо в приложении! 🎧

### 🔧 Технологии
- **Frontend:** React, Vite, Tailwind CSS, Framer Motion
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy
- **AI/ML:** CREPE (pitch detection), OpenSMILE (timbre), OpenAI Whisper (embeddings)
- **Integrations:** Spotify Web API (Embeds)

---

## 🚀 Быстрый старт

### 1. Установка и настройка

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend (в другом терминале)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Настройка базы данных
createdb edinorok
cp .env.example .env
# Отредактируй .env (DATABASE_URL, API keys)

# Запуск сервера
uvicorn app.main:app --host 0.0.0.0 --port 8086 --reload
```
```

### 3. Обработка данных

```bash
# Обновить жанры артистов
python -m scripts.update_genres

# Обработать песни из папки songs/
python -m scripts.process_songs

# Добавить Spotify ID к существующим песням
python -m scripts.add_spotify_ids --limit 10
```
---

## 🎯 Основные команды

### Frontend
```bash
cd frontend
npm run dev          # Запуск dev сервера
npm run build        # Сборка для продакшн
npm run preview      # Предпросмотр продакшн сборки
```

### Backend
```bash
cd backend
source venv/bin/activate

# Запуск сервера
uvicorn app.main:app --host 0.0.0.0 --port 8086 --reload

# Обработка данных
python -m scripts.process_artists          # Обработать вокалы артистов
python -m scripts.process_songs            # Обработать песни
python -m scripts.update_genres            # Обновить жанры
python -m scripts.add_spotify_ids          # Добавить Spotify ID
python -m scripts.add_embeddings           # Добавить OpenAI embeddings

# Утилиты
python -m scripts.fix_permissions          # Исправить права БД
python -m scripts.migrate_spotify_fields   # Миграция для Spotify
```

---


### Tech Stack Details

**Audio Processing:**
- `librosa` - audio preprocessing, feature extraction
- `CREPE` - pitch detection (neural network)
- `OpenSMILE` - timbre features (eGeMAPS)
- `soundfile` - audio I/O

**Machine Learning:**
- `OpenAI Whisper API` - voice embeddings
- `scikit-learn` - similarity calculations
- `numpy` - numerical operations

**Backend:**
- `FastAPI` - modern async web framework
- `SQLAlchemy` - ORM with async support
- `Pydantic` - data validation
- `httpx` - async HTTP client (Spotify API)

**Frontend:**
- `React 18` - UI library
- `Vite` - build tool
- `Tailwind CSS` - utility-first CSS
- `Framer Motion` - animations
- `Lucide React` - icons
