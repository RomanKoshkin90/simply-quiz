#!/bin/bash
set -e

# Функция для остановки процессов при выходе
cleanup() {
    echo "🛑 Остановка сервисов..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait
    exit 0
}

trap cleanup SIGTERM SIGINT

# Запуск backend
echo "🚀 Запуск Backend (FastAPI)..."
cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 8086 &
BACKEND_PID=$!

# Небольшая задержка для запуска backend
sleep 2

# Запуск frontend (serve статику через простой HTTP сервер)
echo "🚀 Запуск Frontend (Static files)..."
cd /app/frontend/dist

# Используем Python HTTP сервер для статики (встроенный)
python3 -m http.server 5173 --bind 0.0.0.0 &
FRONTEND_PID=$!

echo "✅ Backend запущен на http://0.0.0.0:8086"
echo "✅ Frontend запущен на http://0.0.0.0:5173"
echo "📊 Ожидание запросов..."

# Ждем завершения процессов
wait $BACKEND_PID $FRONTEND_PID
