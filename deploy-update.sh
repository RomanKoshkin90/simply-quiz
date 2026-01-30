#!/bin/bash
# Скрипт для обновления Edinorok на сервере
# Использование: ./deploy-update.sh [backend|frontend|all]

set -e  # Остановиться при ошибке

COMPONENT=${1:-all}
PROJECT_DIR="/opt/simply-quiz"

echo "🚀 Обновление Edinorok..."
echo "Компонент: $COMPONENT"

# Функция для вывода с цветами
print_success() { echo -e "\033[0;32m✓ $1\033[0m"; }
print_error() { echo -e "\033[0;31m✗ $1\033[0m"; }
print_info() { echo -e "\033[0;34mℹ $1\033[0m"; }

# Проверка, что скрипт запущен из правильной директории
cd "$PROJECT_DIR" || { print_error "Директория $PROJECT_DIR не найдена"; exit 1; }

# Получаем последние изменения
print_info "Получаем последние изменения из git..."
git pull origin main || { print_error "Не удалось выполнить git pull"; exit 1; }
print_success "Git pull выполнен"

# Обновление Backend
if [ "$COMPONENT" = "backend" ] || [ "$COMPONENT" = "all" ]; then
    print_info "Обновляем Backend..."

    cd "$PROJECT_DIR/backend"

    # Проверяем, изменился ли requirements.txt
    if git diff HEAD@{1} HEAD --name-only | grep -q "requirements.txt"; then
        print_info "Обнаружены изменения в requirements.txt, устанавливаем зависимости..."
        source venv/bin/activate
        pip install -r requirements.txt
        print_success "Зависимости обновлены"
    fi

    # Перезапускаем backend
    print_info "Перезапускаем backend service..."
    systemctl restart edinorok-backend

    # Ждём 2 секунды
    sleep 2

    # Проверяем статус
    if systemctl is-active --quiet edinorok-backend; then
        print_success "Backend успешно перезапущен"
    else
        print_error "Backend не запустился! Проверьте логи: journalctl -u edinorok-backend -n 50"
        exit 1
    fi
fi

# Обновление Frontend
if [ "$COMPONENT" = "frontend" ] || [ "$COMPONENT" = "all" ]; then
    print_info "Обновляем Frontend..."

    cd "$PROJECT_DIR/frontend"

    # Проверяем, изменился ли package.json
    if git diff HEAD@{1} HEAD --name-only | grep -q "package.json"; then
        print_info "Обнаружены изменения в package.json, устанавливаем зависимости..."
        npm install
        print_success "Зависимости обновлены"
    fi

    # Собираем frontend
    print_info "Собираем frontend..."
    npm run build
    print_success "Frontend собран"
fi

print_success "Обновление завершено!"

# Показываем статус сервисов
echo ""
print_info "Статус сервисов:"
systemctl status edinorok-backend --no-pager -l | head -10
systemctl status nginx --no-pager -l | head -5

echo ""
print_success "Всё готово! 🎉"
print_info "Проверьте сайт: https://quiz.simplyonline.ru"
