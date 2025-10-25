# === Этап 1: Сборка зависимостей ===
FROM python:3.10-alpine AS builder

# Установка зависимостей для компиляции Pillow
RUN apk add --no-cache \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# === Этап 2: Финальный образ ===
FROM python:3.10-alpine

# Установка runtime-зависимостей для Pillow
RUN apk add --no-cache \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev

# Создание пользователя без root-прав
RUN adduser -D appuser
USER appuser

WORKDIR /app

# Копируем только необходимое
COPY --chown=appuser:appuser --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

# Добавляем /home/appuser/.local/bin в PATH
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["flask", "run"]