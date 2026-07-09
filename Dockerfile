FROM python:3.11-slim

# تثبيت مكتبة النظام الأساسية لحل مشكلة libsqlite3 نهائياً
RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    libsqlite3-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# تثبيت الحزم والمكتبات المطلوبة
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ بقية ملفات المشروع
COPY . .

# تشغيل التطبيق بالمنفذ الديناميكي الممنوح من Railway
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
