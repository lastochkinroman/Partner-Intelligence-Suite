FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя приложения
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY ./app /app

# Копируем скрипт запуска
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/documents && \
    chown -R appuser:appuser /app

# Переключаемся на пользователя приложения
USER appuser

# Экспортируем порт (опционально для веб-интерфейса)
EXPOSE 8000

# Точка входа
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "app.bot"]
