# 🚀 Инструкция по деплою на VPS (Fedora)

Полная инструкция по развертыванию Edinorok на VPS с Fedora.

**Домен:** quiz.simplyonline.ru
**Путь на сервере:** /opt/simply-quiz
**Stack:** React + FastAPI + PostgreSQL + Nginx

---

## 📋 Предварительные требования

- VPS с Fedora
- Root доступ или sudo
- Домен настроен на IP сервера (A-запись quiz.simplyonline.ru → IP)
- Код уже склонирован в `/opt/simply-quiz`

---

## 🔧 Шаг 1: Установка системных зависимостей

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Обновите систему
dnf update -y

# Установите базовые инструменты
dnf install -y git nginx postgresql-server postgresql-contrib certbot python3-certbot-nginx

# Установите Python 3.12 и зависимости для сборки
dnf install -y python3.12 python3.12-devel gcc gcc-c++ gcc-gfortran \
    openblas-devel libsndfile-devel ffmpeg portaudio-devel

# Установите Node.js 20.x для фронтенда
dnf install -y nodejs npm

# Проверьте версии
python3.12 --version  # Должно быть 3.12.x
node --version        # Должно быть v20.x или выше
npm --version
```

---

## 🗃️ Шаг 2: Настройка PostgreSQL

```bash
# Инициализируйте PostgreSQL (только первый раз)
postgresql-setup --initdb

# Запустите и добавьте в автозагрузку
systemctl start postgresql
systemctl enable postgresql

# Создайте базу данных и пользователя
sudo -u postgres psql <<EOF
CREATE DATABASE edinorok;
CREATE USER edinorok_user WITH PASSWORD 'YOUR_STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON DATABASE edinorok TO edinorok_user;
\c edinorok
GRANT ALL ON SCHEMA public TO edinorok_user;
EOF

# Настройте pg_hba.conf для локального доступа
echo "local   edinorok        edinorok_user                           md5" | \
    sudo tee -a /var/lib/pgsql/data/pg_hba.conf

# Перезапустите PostgreSQL
systemctl restart postgresql

# Проверьте подключение
psql -U edinorok_user -d edinorok -h localhost -W
# Введите пароль, затем выйдите: \q
```

---

## 🐍 Шаг 3: Настройка Backend

### 3.1. Создайте виртуальное окружение

```bash
cd /opt/simply-quiz/backend

# Создайте venv с Python 3.12
python3.12 -m venv venv

# Активируйте
source venv/bin/activate

# Обновите pip
pip install --upgrade pip setuptools wheel

# Установите зависимости (займет 5-10 минут)
pip install -r requirements.txt

# Проверьте, что всё установилось
python -c "import fastapi; import tensorflow; print('✓ OK')"
```

### 3.2. Создайте .env файл

```bash
cat > /opt/simply-quiz/backend/.env <<'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://edinorok_user:YOUR_STRONG_PASSWORD_HERE@localhost/edinorok

# API Keys (получите на https://platform.openai.com)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Spotify API (получите на https://developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret

# Server
HOST=0.0.0.0
PORT=8086
RELOAD=false
WORKERS=4

# CORS
ALLOWED_ORIGINS=https://quiz.simplyonline.ru,http://quiz.simplyonline.ru

# Uploads
UPLOAD_DIR=/opt/simply-quiz/backend/uploads
MAX_UPLOAD_SIZE=52428800  # 50MB

# Environment
ENVIRONMENT=production
EOF

# Замените YOUR_STRONG_PASSWORD_HERE на реальный пароль БД
nano /opt/simply-quiz/backend/.env
```

### 3.3. Создайте директорию для загрузок

```bash
mkdir -p /opt/simply-quiz/backend/uploads
chmod 755 /opt/simply-quiz/backend/uploads
```

### 3.4. Запустите миграции (если есть alembic)

```bash
cd /opt/simply-quiz/backend
source venv/bin/activate

# Если есть alembic.ini, запустите миграции
# alembic upgrade head

# Или создайте таблицы через скрипт
python -c "from app.db.database import engine, Base; import asyncio; asyncio.run(Base.metadata.create_all(bind=engine))"
```

### 3.5. Создайте systemd service для backend

```bash
cat > /etc/systemd/system/edinorok-backend.service <<'EOF'
[Unit]
Description=Edinorok FastAPI Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/simply-quiz/backend
Environment="PATH=/opt/simply-quiz/backend/venv/bin"
ExecStart=/opt/simply-quiz/backend/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8086 \
    --workers 4 \
    --log-level info

# Автоматический перезапуск при падении
Restart=always
RestartSec=10

# Лимиты
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузите systemd
systemctl daemon-reload

# Запустите backend
systemctl start edinorok-backend

# Добавьте в автозагрузку
systemctl enable edinorok-backend

# Проверьте статус
systemctl status edinorok-backend

# Посмотрите логи
journalctl -u edinorok-backend -f
```

### 3.6. Проверьте работу backend

```bash
# Проверьте, что backend слушает порт 8086
ss -tlnp | grep 8086

# Проверьте API
curl http://localhost:8086/api/health
# Должен вернуть: {"status":"ok"}
```

---

## 🎨 Шаг 4: Сборка и настройка Frontend

### 4.1. Настройте переменные окружения

```bash
cd /opt/simply-quiz/frontend

# Создайте .env для продакшн
cat > .env.production <<'EOF'
VITE_API_URL=https://quiz.simplyonline.ru/api
EOF
```

### 4.2. Установите зависимости и соберите

```bash
cd /opt/simply-quiz/frontend

# Установите зависимости
npm install

# Соберите для продакшн
npm run build

# Проверьте, что создалась папка dist/
ls -la dist/
```

---

## 🌐 Шаг 5: Настройка Nginx

### 5.1. Создайте конфигурацию Nginx

```bash
cat > /etc/nginx/conf.d/quiz.simplyonline.ru.conf <<'EOF'
# Upstream для backend
upstream edinorok_backend {
    server 127.0.0.1:8086;
    keepalive 32;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name quiz.simplyonline.ru;

    # Для certbot
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS сервер
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name quiz.simplyonline.ru;

    # SSL сертификаты (будут настроены certbot'ом)
    ssl_certificate /etc/letsencrypt/live/quiz.simplyonline.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/quiz.simplyonline.ru/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/quiz.simplyonline.ru/chain.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Логи
    access_log /var/log/nginx/quiz_access.log;
    error_log /var/log/nginx/quiz_error.log;

    # Увеличенный размер загружаемых файлов (для аудио)
    client_max_body_size 50M;

    # Frontend (React SPA)
    location / {
        root /opt/simply-quiz/frontend/dist;
        try_files $uri $uri/ /index.html;

        # Кэширование статики
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://edinorok_backend/api/;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (если нужно)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Таймауты для долгих запросов (обработка аудио)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Healthcheck
    location /health {
        proxy_pass http://edinorok_backend/api/health;
        access_log off;
    }
}
EOF

# Проверьте конфигурацию
nginx -t

# Если OK, перезапустите Nginx
systemctl restart nginx
systemctl enable nginx
```

---

## 🔒 Шаг 6: Настройка SSL с Let's Encrypt

```bash
# Получите SSL сертификат
certbot --nginx -d quiz.simplyonline.ru --non-interactive --agree-tos \
    --email your-email@example.com --redirect

# Certbot автоматически обновит конфигурацию nginx

# Проверьте автообновление сертификата
certbot renew --dry-run

# Сертификат будет автоматически обновляться через systemd timer
systemctl status certbot-renew.timer
```

---

## 🔥 Шаг 7: Настройка Firewall

```bash
# Откройте порты 80 и 443
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# Проверьте правила
firewall-cmd --list-all
```

---

## ✅ Шаг 8: Финальная проверка

### 8.1. Проверьте все сервисы

```bash
# PostgreSQL
systemctl status postgresql

# Backend
systemctl status edinorok-backend
journalctl -u edinorok-backend -n 50

# Nginx
systemctl status nginx
nginx -t
```

### 8.2. Проверьте сайт

```bash
# Проверьте HTTP -> HTTPS редирект
curl -I http://quiz.simplyonline.ru

# Проверьте HTTPS
curl -I https://quiz.simplyonline.ru

# Проверьте API
curl https://quiz.simplyonline.ru/api/health
# Должен вернуть: {"status":"ok"}
```

### 8.3. Откройте в браузере

Перейдите на **https://quiz.simplyonline.ru** и проверьте:
- ✅ Сайт загружается
- ✅ SSL сертификат валиден (зелёный замок)
- ✅ Нет ошибок в консоли браузера (F12)
- ✅ API работает (попробуйте загрузить аудио)

---

## 🔄 Обновление после изменений кода

### Обновление Backend

```bash
cd /opt/simply-quiz
git pull origin main

cd backend
source venv/bin/activate
pip install -r requirements.txt  # если обновились зависимости

# Перезапустите сервис
systemctl restart edinorok-backend

# Проверьте логи
journalctl -u edinorok-backend -f
```

### Обновление Frontend

```bash
cd /opt/simply-quiz
git pull origin main

cd frontend
npm install  # если обновились зависимости
npm run build

# Nginx автоматически подхватит новые файлы
# Очистите кэш браузера (Ctrl+Shift+R)
```

---

## 📊 Мониторинг и логи

### Логи Backend

```bash
# Смотреть логи в реальном времени
journalctl -u edinorok-backend -f

# Последние 100 строк
journalctl -u edinorok-backend -n 100

# Логи за сегодня
journalctl -u edinorok-backend --since today
```

### Логи Nginx

```bash
# Access логи
tail -f /var/log/nginx/quiz_access.log

# Error логи
tail -f /var/log/nginx/quiz_error.log
```

### Мониторинг ресурсов

```bash
# CPU и память
htop

# Диск
df -h

# Сетевые подключения
ss -tulpn | grep -E ':(80|443|8086)'

# Процессы Python
ps aux | grep uvicorn
```

---

## 🐛 Решение проблем

### Backend не запускается

```bash
# Проверьте логи
journalctl -u edinorok-backend -n 100

# Проверьте .env файл
cat /opt/simply-quiz/backend/.env

# Проверьте подключение к БД
cd /opt/simply-quiz/backend
source venv/bin/activate
python -c "from app.db.database import engine; import asyncio; asyncio.run(engine.connect())"

# Проверьте порт 8086
ss -tlnp | grep 8086
```

### Nginx возвращает 502 Bad Gateway

```bash
# Backend не запущен или упал
systemctl status edinorok-backend
systemctl restart edinorok-backend

# Проверьте, что backend слушает 8086
curl http://localhost:8086/api/health
```

### Frontend показывает белый экран

```bash
# Проверьте, что файлы собраны
ls -la /opt/simply-quiz/frontend/dist/

# Пересоберите
cd /opt/simply-quiz/frontend
rm -rf dist/
npm run build

# Проверьте консоль браузера (F12) на ошибки
```

### SSL не работает

```bash
# Проверьте сертификаты
ls -la /etc/letsencrypt/live/quiz.simplyonline.ru/

# Перевыпустите сертификат
certbot --nginx -d quiz.simplyonline.ru --force-renewal

# Проверьте nginx
nginx -t
systemctl restart nginx
```

---

## 🎯 Оптимизация производительности

### Backend

```bash
# Увеличьте количество workers в systemd service
nano /etc/systemd/system/edinorok-backend.service
# Измените --workers 4 на --workers 8 (по количеству CPU)

systemctl daemon-reload
systemctl restart edinorok-backend
```

### PostgreSQL

```bash
# Оптимизируйте PostgreSQL для production
nano /var/lib/pgsql/data/postgresql.conf

# Рекомендуемые настройки (для 4GB RAM):
# shared_buffers = 1GB
# effective_cache_size = 3GB
# maintenance_work_mem = 256MB
# checkpoint_completion_target = 0.9
# wal_buffers = 16MB
# default_statistics_target = 100
# random_page_cost = 1.1
# effective_io_concurrency = 200
# work_mem = 10MB
# min_wal_size = 1GB
# max_wal_size = 4GB

systemctl restart postgresql
```

---

## 🎉 Готово!

Ваш проект теперь доступен на **https://quiz.simplyonline.ru**

### Полезные команды

```bash
# Перезапустить всё
systemctl restart postgresql edinorok-backend nginx

# Проверить статус всех сервисов
systemctl status postgresql edinorok-backend nginx

# Посмотреть логи backend
journalctl -u edinorok-backend -f

# Обновить код
cd /opt/simply-quiz && git pull && \
  systemctl restart edinorok-backend && \
  cd frontend && npm run build
```

---

## 📚 Дополнительно

- Настройте регулярный бэкап БД: `/opt/simply-quiz/backend/scripts/backup_db.sh`
- Настройте monitoring (Prometheus + Grafana)
- Настройте алерты (например, через Telegram бота)
- Настройте CI/CD (GitHub Actions для автодеплоя)

**Удачи! 🚀**
