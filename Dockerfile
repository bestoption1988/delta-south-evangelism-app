FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn --timeout 240 --graceful-timeout 30 --bind 0.0.0.0:${PORT:-8000} app:app"]
