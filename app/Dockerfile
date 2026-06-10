FROM python:3.12-slim

RUN apt update && apt install -y \
    ffmpeg \
    curl \
    atomicparsley \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask \
    requests \
    yt-dlp \
    mutagen

WORKDIR /app
CMD ["python", "app.py"]
