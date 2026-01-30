# 🐳 Docker инструкция для Edinorok

Запуск backend и frontend в одном контейнере.

---

## 📋 Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

```bash
# 1. Создай .env файл (опционально)
cp backend/env.example .env
# Отредактируй .env при необходимости

# 2. Запусти все сервисы (app + database)
docker-compose up -d

# 3. Проверь логи
docker-compose logs -f

# 4. Открой в браузере
# Frontend: http://localhost:5173
# Backend API: http://localhost:8086
# API Docs: http://localhost:8086/docs
```

### Вариант 2: Только Docker (без compose)

```bash
# 1. Собери образ
docker build -t edinorok:latest .

# 2. Запусти контейнер
docker run -d \
  --name edinorok-app \
  -p 8086:8086 \
  -p 5173:5173 \
  -e DATABASE_URL=postgresql://user:password@host:5432/edinorok \
  -v $(pwd)/backend/uploads:/app/backend/uploads \
  edinorok:latest

# 3. Проверь логи
docker logs -f edinorok-app
```

---

## 🔧 Настройка

### Переменные окружения

Создай `.env` файл в корне проекта:

```env
# Database (для docker-compose используется автоматически)
DATABASE_URL=postgresql://edinorok_user:password@db:5432/edinorok

# OpenAI (опционально)
OPENAI_API_KEY=твой_ключ
OPENAI_PROXY_HOST=146.19.25.182
OPENAI_PROXY_PORT=62267
OPENAI_PROXY_USERNAME=CVQu5RG7
OPENAI_PROXY_PASSWORD=aktr7K7P
OPENAI_PROXY_TYPE=socks5
USE_OPENAI_FOR_USER_ANALYSIS=True

# Yandex Music
YANDEX_MUSIC_TOKEN=твой_токен
```

### Volumes (сохранение данных)

В `docker-compose.yml` настроены volumes:
- `./backend/uploads` - загруженные аудио файлы
- `./backend/songs` - песни для обработки
- `./backend/artist_vocals` - вокалы артистов
- `postgres_data` - база данных PostgreSQL

---

## 🚀 Команды

### Docker Compose

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Логи
docker-compose logs -f edinorok

# Пересборка образа
docker-compose build --no-cache

# Выполнить команду в контейнере
docker-compose exec edinorok bash
```

### Docker (без compose)

```bash
# Сборка образа
docker build -t edinorok:latest .

# Запуск
docker run -d --name edinorok-app -p 8086:8086 -p 5173:5173 edinorok:latest

# Остановка
docker stop edinorok-app

# Удаление
docker rm edinorok-app

# Логи
docker logs -f edinorok-app

# Выполнить команду в контейнере
docker exec -it edinorok-app bash
```

---

## 🗄️ Инициализация базы данных

После первого запуска нужно создать таблицы:

```bash
# Через docker-compose
docker-compose exec edinorok python -c "
import asyncio
from app.db.database import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())
"

# Или через прямой доступ к контейнеру
docker exec -it edinorok-app bash
cd /app/backend
python -c "..." # та же команда
```

---

## 📊 Обработка данных

### Обработка артистов

```bash
docker-compose exec edinorok bash
cd /app/backend
python -m scripts.process_artists
```

### Обработка песен

```bash
docker-compose exec edinorok bash
cd /app/backend
python -m scripts.process_songs
```

### Добавление embeddings

```bash
docker-compose exec edinorok bash
cd /app/backend
python -m scripts.add_embeddings
```

---

## 🔍 Проверка работы

1. **Frontend:** http://localhost:5173
2. **Backend API:** http://localhost:8086/docs
3. **Health check:** http://localhost:8086/health (если есть endpoint)

---

## 🐛 Отладка

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Только backend
docker-compose logs -f edinorok

# Только database
docker-compose logs -f db
```

### Вход в контейнер

```bash
docker-compose exec edinorok bash
# или
docker exec -it edinorok-app bash
```

### Проверка процессов

```bash
docker-compose exec edinorok ps aux
```

---

## 🔄 Обновление

```bash
# 1. Получи последние изменения
git pull

# 2. Пересобери образ
docker-compose build --no-cache

# 3. Перезапусти
docker-compose down
docker-compose up -d
```

---

## 📦 Production деплой

Для production рекомендуется:

1. **Использовать Nginx** как reverse proxy перед контейнером
2. **Настроить SSL** через Let's Encrypt
3. **Использовать volumes** для персистентности данных
4. **Настроить мониторинг** (health checks, logs)

Пример Nginx конфигурации:

```nginx
server {
    listen 80;
    server_name твой_домен.com;
    
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
    }
    
    location /api {
        proxy_pass http://localhost:8086;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## ⚠️ Важные моменты

1. **Порты:**
   - `8086` - Backend API
   - `5173` - Frontend
   - `5432` - PostgreSQL (только в docker-compose)

2. **Volumes:**
   - Аудио файлы сохраняются в `./backend/uploads`
   - База данных в volume `postgres_data`

3. **Переменные окружения:**
   - Для docker-compose используй `.env` файл
   - Для docker run передавай через `-e`

4. **Безопасность:**
   - Не коммить `.env` файлы
   - Используй сильные пароли для БД
   - Настрой файрвол на сервере

---

**Готово! Проект работает в Docker!** 🐳
