# Usa una imagen base de Python ligera
FROM python:3.11-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Instala dependencias del sistema necesarias para Chrome, Playwright y FFmpeg
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    ffmpeg \
    curl \
    libnss3 \
    libgconf-2-4 \
    libxi6 \
    libxkbcommon-x11-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxshmfence1 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar Google Chrome estable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install \
    && rm google-chrome-stable_current_amd64.deb

# Instalar ChromeDriver
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Copia el archivo de requisitos e instala dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright y navegadores (por si los usás en el bot)
RUN pip install playwright
RUN playwright install --with-deps

# Copia el resto de la aplicación
COPY . /app/

# Define el comando por defecto para ejecutar el bot
CMD ["python", "botTelegram.py"]


