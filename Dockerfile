# Usar una imagen base de Python 3.12
FROM python:3.12-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    curl \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# Copiar los archivos necesarios
COPY requirements.txt .
COPY fastapi_backend/ fastapi_backend/
COPY src/ src/

# Crear directorio para logs
RUN mkdir -p logs

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Inicializar la base de datos
RUN cd src && python3 -c "from db.analisis_db import init_db; init_db()" || echo "Database already exists"

# Exponer puertos necesarios
EXPOSE 8000
EXPOSE 8501

# Script de inicio
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# Comando por defecto
ENTRYPOINT ["/docker-entrypoint.sh"]