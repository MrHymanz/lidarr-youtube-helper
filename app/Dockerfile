FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    ca-certificates \
    atomicparsley \
    && rm -rf /var/lib/apt/lists/*

# Installeer Deno system-wide voor yt-dlp
RUN curl -fsSL https://deno.land/install.sh \
    | DENO_INSTALL=/usr/local sh \
    && deno --version

RUN pip install --no-cache-dir \
    flask \
    requests \
    "yt-dlp[default]" \
    mutagen

WORKDIR /app

CMD ["python", "app.py"]