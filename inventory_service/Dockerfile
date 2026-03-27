# FILE: inventory_service/Dockerfile

FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Команда за замовчуванням
CMD ["python", "-u", "inventory_worker.py"]