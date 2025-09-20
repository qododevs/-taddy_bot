# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем зависимости ОС (если понадобятся)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# Создаем пользователя (не root — безопаснее)
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Запускаем бота
CMD ["python", "bot.py"]