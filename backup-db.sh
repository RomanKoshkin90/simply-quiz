#!/bin/bash
# Скрипт для бэкапа базы данных PostgreSQL
# Использование: ./backup-db.sh

set -e

# Настройки
DB_NAME="edinorok"
DB_USER="edinorok_user"
BACKUP_DIR="/opt/simply-quiz/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/edinorok_$DATE.sql.gz"
KEEP_DAYS=7  # Хранить бэкапы за последние 7 дней

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Создание бэкапа базы данных...${NC}"

# Создаём директорию для бэкапов
mkdir -p "$BACKUP_DIR"

# Создаём бэкап
echo -e "${BLUE}Экспортируем базу $DB_NAME...${NC}"
PGPASSWORD=$(grep DATABASE_URL /opt/simply-quiz/backend/.env | cut -d':' -f3 | cut -d'@' -f1) \
    pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Бэкап создан: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
else
    echo -e "${RED}✗ Ошибка создания бэкапа${NC}"
    exit 1
fi

# Удаляем старые бэкапы
echo -e "${BLUE}Удаляем бэкапы старше $KEEP_DAYS дней...${NC}"
find "$BACKUP_DIR" -name "edinorok_*.sql.gz" -type f -mtime +$KEEP_DAYS -delete

# Показываем список бэкапов
echo -e "${BLUE}Список бэкапов:${NC}"
ls -lh "$BACKUP_DIR"/edinorok_*.sql.gz 2>/dev/null || echo "Нет бэкапов"

echo -e "${GREEN}✓ Готово!${NC}"

# Инструкция по восстановлению
echo ""
echo -e "${BLUE}Для восстановления из бэкапа:${NC}"
echo "gunzip < $BACKUP_FILE | psql -U $DB_USER -h localhost -d $DB_NAME"
