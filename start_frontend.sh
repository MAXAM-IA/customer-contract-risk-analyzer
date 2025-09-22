#!/bin/bash

# Script para iniciar solo el frontend (Streamlit) del AI Risk Analyzer
# Uso: ./start_frontend.sh

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🖥️  Iniciando Frontend AI Risk Analyzer...${NC}"

# Función de limpieza
cleanup() {
    echo -e "\n${YELLOW}⏹️  Deteniendo frontend...${NC}"
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    exit 0
}

trap cleanup EXIT INT TERM

# Verificar directorio
if [ ! -d "src" ] || [ ! -f "src/main.py" ]; then
    echo -e "${RED}❌ Error: No se encontró src/main.py${NC}"
    echo -e "${RED}   Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Limpiar puerto si está ocupado
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Puerto 8501 ocupado. Liberando...${NC}"
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo -e "${BLUE}🐍 Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Verificar Streamlit
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}❌ Streamlit no está instalado${NC}"
    echo -e "${YELLOW}💡 Ejecuta: pip install streamlit${NC}"
    exit 1
fi

# Inicializar BD si es necesario
echo -e "${BLUE}🗄️  Verificando base de datos...${NC}"
cd src
python3 -c "from db.analisis_db import init_db; init_db(); print('✅ BD verificada')" 2>/dev/null || echo -e "${YELLOW}⚠️  BD ya existe${NC}"

# Iniciar frontend
echo -e "${GREEN}🚀 Iniciando Streamlit en puerto 8501...${NC}"
echo -e "${BLUE}🌐 URL: http://localhost:8501${NC}"
echo -e "${YELLOW}📝 Presiona Ctrl+C para detener${NC}"
echo

# Ejecutar Streamlit
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

cd ..
