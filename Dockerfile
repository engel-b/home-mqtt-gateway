FROM python:3.13-slim

RUN apk add --no-cache \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

# running cron in the foreground
CMD ["python", "main.py"]
