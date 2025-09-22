#!/bin/bash

# Script para iniciar solo el backend (FastAPI) del AI Risk Analyzer
# Uso: ./start_backend.sh

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}� Iniciando Backend AI Risk Analyzer...${NC}"

# Función de limpieza
cleanup() {
    echo -e "\n${YELLOW}⏹️  Deteniendo backend...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup EXIT INT TERM

# Verificar directorio
if [ ! -d "fastapi_backend" ] || [ ! -f "fastapi_backend/main.py" ]; then
    echo -e "${RED}❌ Error: No se encontró fastapi_backend/main.py${NC}"
    echo -e "${RED}   Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Limpiar puerto si está ocupado
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Puerto 8000 ocupado. Liberando...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo -e "${BLUE}🐍 Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Verificar uvicorn
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo -e "${RED}❌ Uvicorn no está instalado${NC}"
    echo -e "${YELLOW}💡 Ejecuta: pip install uvicorn fastapi${NC}"
    exit 1
fi

# Inicializar BD si es necesario
echo -e "${BLUE}🗄️  Verificando base de datos...${NC}"
cd src
python3 -c "from db.analisis_db import init_db; init_db(); print('✅ BD verificada')" 2>/dev/null || echo -e "${YELLOW}⚠️  BD ya existe${NC}"
cd ..

# Crear directorio de progreso si no existe
mkdir -p fastapi_backend/progreso

# Verificar variables de entorno
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo -e "${YELLOW}   Crea .env con GOOGLE_API_KEY=tu_api_key${NC}"
fi

# Iniciar backend
echo -e "${GREEN}🚀 Iniciando FastAPI en puerto 8000...${NC}"
echo -e "${BLUE}🌐 API: http://localhost:8000${NC}"
echo -e "${BLUE}📚 Docs: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}📝 Presiona Ctrl+C para detener${NC}"
echo

# Cambiar al directorio del backend
cd fastapi_backend

# Ejecutar FastAPI con uvicorn
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

cd ..

echo "📂 Directorio de trabajo: $(pwd)"

# Verificar Python
python_version=$(python3 --version 2>/dev/null || echo "No encontrado")
echo "🐍 Python: $python_version"

# Verificar e instalar dependencias
echo "📦 Verificando dependencias..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Instalando dependencias..."
    pip3 install -r requirements.txt
fi

# Cambiar al directorio del backend
cd fastapi_backend

echo "🌐 Iniciando servidor FastAPI en http://localhost:8000"
echo "📊 Logs del sistema se guardan en analisis.log"
echo "🛑 Presionar Ctrl+C para detener"
echo ""

# Iniciar el servidor
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
