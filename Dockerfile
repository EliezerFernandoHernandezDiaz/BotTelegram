FROM python:3.11-slim

WORKDIR /app

# Instalar herramientas de compilación + ffmpeg
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la app
COPY . .

# Ejecutar el bot
CMD ["python", "botTelegram.py"]
