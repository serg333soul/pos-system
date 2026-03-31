# FILE: inventory_service/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запускаємо сервер FastAPI для керування складом
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]