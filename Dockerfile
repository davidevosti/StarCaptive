FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY portal/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY portal/ .

RUN mkdir -p /data

ENV DATABASE_PATH=/data/sessions.db
ENV PORTAL_HOST=0.0.0.0
ENV PORTAL_PORT=5000
ENV LOG_LEVEL=INFO

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
