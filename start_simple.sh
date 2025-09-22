#!/bin/bash

# Script simple para iniciar el AI Risk Analyzer
# Uso: ./start_simple.sh

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando AI Risk Analyzer...${NC}"

# Limpiar puertos si están ocupados
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8501 | xargs kill -9 2>/dev/null || true

# Función de limpieza
cleanup() {
    echo -e "\n${YELLOW}⏹️  Deteniendo servicios...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup EXIT INT TERM

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Instalar dependencias si es necesario
if [ ! -f ".deps_installed" ]; then
    echo -e "${BLUE}📦 Instalando dependencias...${NC}"
    pip install -q -r requirements.txt
    touch .deps_installed
fi

# Inicializar BD
cd src && python3 -c "from db.analisis_db import init_db; init_db()" 2>/dev/null || true && cd ..

# Iniciar backend
echo -e "${BLUE}🔧 Iniciando backend...${NC}"
cd fastapi_backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /dev/null 2>&1 &
cd ..

# Esperar backend
sleep 3

# Iniciar frontend
echo -e "${BLUE}🖥️  Iniciando frontend...${NC}"
cd src
streamlit run main.py --server.port 8501 --server.headless true > /dev/null 2>&1 &
cd ..

# Esperar frontend
sleep 3

echo -e "${GREEN}✅ Sistema iniciado!${NC}"
echo -e "${GREEN}🌐 Frontend: http://localhost:8501${NC}"
echo -e "${GREEN}⚡ Backend: http://localhost:8000${NC}"
echo -e "${YELLOW}📝 Presiona Ctrl+C para detener${NC}"

# Mantener script corriendo
while true; do
    sleep 1
done
