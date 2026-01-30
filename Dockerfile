# Multi-stage build для оптимизации размера образа

# ============================================
# Stage 1: Frontend Build
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Копируем package файлы
COPY frontend/package*.json ./

# Устанавливаем зависимости
RUN npm ci

# Копируем исходники frontend
COPY frontend/ ./

# Собираем production build
RUN npm run build

# ============================================
# Stage 2: Backend + Frontend (Final)
# ============================================
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Создаем виртуальное окружение для backend
RUN python3 -m venv /app/backend/venv
ENV PATH="/app/backend/venv/bin:$PATH"

# Копируем requirements и устанавливаем Python зависимости в venv
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Копируем backend код
COPY backend/ ./backend/

# Копируем собранный frontend из предыдущего stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Копируем скрипт запуска
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Создаем директории для uploads
RUN mkdir -p /app/backend/uploads /app/backend/songs /app/backend/artist_vocals && \
    chmod -R 755 /app/backend/uploads /app/backend/songs /app/backend/artist_vocals

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Порт для backend
EXPOSE 8086

# Порт для frontend (если используем dev сервер, иначе только через nginx)
EXPOSE 5173

# Запуск через entrypoint скрипт
ENTRYPOINT ["./docker-entrypoint.sh"]
