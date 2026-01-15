FROM python:3.9-slim

WORKDIR /app

# Копіюємо requirements і встановлюємо залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- ВИПРАВЛЕННЯ ТУТ ---
# Копіюємо ВСІ файли з поточної папки (main.py, schemas.py і т.д.)
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]