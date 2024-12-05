# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo de requisitos e instala dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia los archivos de la aplicación
COPY . /app/

# Da permisos de ejecución al script de instalación de FFmpeg
RUN chmod +x /app/install_ffmpeg.sh
RUN ./install_ffmpeg.sh

# Define el comando de inicio del bot (modifica según tu caso)
CMD ["python", "botTelegram.py"]
