#!/bin/bash
# Скрипт для проверки статуса всех компонентов Edinorok

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

check_service() {
    local service=$1
    local display_name=$2

    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓${NC} $display_name: ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $display_name: ${RED}STOPPED${NC}"
        return 1
    fi
}

check_port() {
    local port=$1
    local service_name=$2

    if ss -tlnp | grep -q ":$port "; then
        echo -e "${GREEN}✓${NC} $service_name (порт $port): ${GREEN}LISTENING${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name (порт $port): ${RED}NOT LISTENING${NC}"
        return 1
    fi
}

check_url() {
    local url=$1
    local name=$2

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✓${NC} $name: ${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}✗${NC} $name: ${RED}FAILED${NC}"
        return 1
    fi
}

# Заголовок
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║        Edinorok Status Check                   ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверка сервисов
print_header "🔧 Системные сервисы"
check_service "postgresql" "PostgreSQL"
check_service "edinorok-backend" "Backend (FastAPI)"
check_service "nginx" "Nginx"

# Проверка портов
print_header "🔌 Сетевые порты"
check_port "5432" "PostgreSQL"
check_port "8086" "Backend API"
check_port "80" "HTTP"
check_port "443" "HTTPS"

# Проверка URL
print_header "🌐 HTTP эндпоинты"
check_url "http://localhost:8086/api/health" "Backend Health (internal)"
check_url "https://quiz.simplyonline.ru" "Frontend (HTTPS)"
check_url "https://quiz.simplyonline.ru/api/health" "API через Nginx"

# Проверка диска
print_header "💾 Дисковое пространство"
df -h /opt/simply-quiz | tail -1 | awk '{print "Использовано: " $3 " из " $2 " (" $5 ")"}'

# Проверка памяти
print_header "🧠 Память"
free -h | grep "Mem:" | awk '{print "Использовано: " $3 " из " $2}'

# Последние ошибки backend
print_header "📜 Последние логи Backend (5 строк)"
journalctl -u edinorok-backend -n 5 --no-pager | sed 's/^/  /'

# CPU процессов
print_header "⚡ Процессы Python (Backend)"
ps aux | grep "[u]vicorn" | awk '{print $2, $3"% CPU", $4"% MEM", $11, $12, $13}'

# SSL сертификат
print_header "🔒 SSL Сертификат"
if [ -f "/etc/letsencrypt/live/quiz.simplyonline.ru/cert.pem" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/quiz.simplyonline.ru/cert.pem | cut -d= -f2)
    echo -e "${GREEN}✓${NC} Сертификат действителен до: $EXPIRY"
else
    echo -e "${YELLOW}⚠${NC} Сертификат не найден"
fi

# Итоговый статус
print_header "📊 Итог"
if systemctl is-active --quiet postgresql && \
   systemctl is-active --quiet edinorok-backend && \
   systemctl is-active --quiet nginx && \
   curl -s https://quiz.simplyonline.ru/api/health | grep -q "ok"; then
    echo -e "${GREEN}✓ Все системы работают нормально!${NC} 🎉"
    exit 0
else
    echo -e "${YELLOW}⚠ Обнаружены проблемы. Проверьте детали выше.${NC}"
    exit 1
fi
