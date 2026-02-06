#!/bin/bash
set -e

echo "🚀 Запуск Business Intelligence Bot..."

# Ждем готовности базы данных
echo "⏳ Ожидание MySQL..."
while ! nc -z mysql 3306; do
  sleep 1
done
echo "✅ MySQL готов"

# Ждем готовности Redis
echo "⏳ Ожидание Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "✅ Redis готов"

# Запуск миграций (если используем Alembic)
# alembic upgrade head

# Запуск основного приложения
echo "🤖 Запуск Telegram бота..."
exec "$@"
