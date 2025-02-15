# Usa una imagen base de Python ligera
FROM python:3.11-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para Chrome y FFmpeg
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
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install

# Instalar ChromeDriver de forma manual con una versión específica
RUN wget -q https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Copia el archivo de requisitos e instala dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright y sus navegadores
RUN pip install playwright
RUN playwright install --with-deps

# Copia los archivos de la aplicación al contenedor
COPY . /app/

# Da permisos de ejecución al script de instalación de FFmpeg y lo ejecuta (si existe)
RUN chmod +x /app/install_ffmpeg.sh && /bin/bash /app/install_ffmpeg.sh || echo "FFmpeg script no encontrado, continuando..."

# Define el comando de inicio del bot
CMD ["python", "botTelegram.py"]


