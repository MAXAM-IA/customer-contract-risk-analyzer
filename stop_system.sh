#!/bin/bash

# Script para detener el AI Risk Analyzer
# Uso: ./stop_system.sh

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⏹️  Deteniendo AI Risk Analyzer...${NC}"

# Buscar y matar procesos del backend
echo -e "${YELLOW}🔧 Deteniendo backend (puerto 8000)...${NC}"
BACKEND_PIDS=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Backend detenido${NC}"
else
    echo -e "${YELLOW}⚠️  Backend no estaba corriendo${NC}"
fi

# Buscar y matar procesos del frontend
echo -e "${YELLOW}🖥️  Deteniendo frontend (puerto 8501)...${NC}"
FRONTEND_PIDS=$(lsof -ti:8501 2>/dev/null)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "$FRONTEND_PIDS" | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Frontend detenido${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend no estaba corriendo${NC}"
fi

# Buscar procesos Python relacionados con uvicorn o streamlit
echo -e "${YELLOW}🔍 Limpiando procesos relacionados...${NC}"
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "streamlit.*main.py" 2>/dev/null || true

# Verificar que los puertos estén libres
sleep 2

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Puerto 8000 aún está ocupado${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
else
    echo -e "${GREEN}✅ Puerto 8000 liberado${NC}"
fi

if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Puerto 8501 aún está ocupado${NC}"
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
else
    echo -e "${GREEN}✅ Puerto 8501 liberado${NC}"
fi

echo -e "${GREEN}🎉 Sistema detenido completamente${NC}"
