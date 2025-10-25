# Используем официальный образ Python с нужной версией
FROM python:3.10-slim

# Задаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы с зависимостями (requirements.txt)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . .

# Открываем порт, на котором будет работать Flask (обычно 5000)
EXPOSE 5000

# Устанавливаем переменную окружения для Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Команда для запуска Flask-приложения
CMD ["flask", "run"]

