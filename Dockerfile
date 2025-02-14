# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo de requisitos e instala dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright y sus navegadores
RUN pip install playwright
RUN playwright install --with-deps

# Copia los archivos de la aplicación
COPY . /app/

# Da permisos de ejecución al script de instalación de FFmpeg y lo ejecuta
RUN chmod +x /app/install_ffmpeg.sh && /bin/bash /app/install_ffmpeg.sh

# Define el comando de inicio del bot
CMD ["python", "botTelegram.py"]
