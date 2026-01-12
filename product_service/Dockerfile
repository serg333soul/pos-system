FROM python:3.9-slim

WORKDIR /app

# Спочатку копіюємо вимоги і ставимо бібліотеки (щоб кешувалось)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ТЕПЕР КОПІЮЄМО ВСЕ (включаючи models.py, schemas.py, database.py)
COPY . .

# Запускаємо
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]