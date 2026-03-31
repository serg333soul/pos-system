# FILE: finance_service/Dockerfile

# Використовуємо легку офіційну версію Python
FROM python:3.10-slim

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Копіюємо файл із залежностями
COPY requirements.txt .

# Встановлюємо бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь інший код нашого мікросервісу
COPY . .

# Команда за замовчуванням (хоча вона перевизначається в docker-compose)
CMD ["python", "-u", "finance_worker.py"]