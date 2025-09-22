#!/bin/bash

# Script para iniciar el backend y frontend del AI Risk Analyzer
# Autor: Sistema AI Risk Analyzer
# Fecha: 2 de julio de 2025

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Función para imprimir con colores
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌${NC} $1"
}

print_info() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️${NC} $1"
}

# Banner de inicio
echo -e "${PURPLE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  AI RISK ANALYZER                          ║"
echo "║              Backend + Frontend Launcher                   ║"
echo "║                                                            ║"
echo "║  🚀 Iniciando sistemas completos...                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ] || [ ! -d "fastapi_backend" ] || [ ! -d "src" ]; then
    print_error "Error: No se encontraron los directorios necesarios"
    print_error "Asegúrate de ejecutar este script desde el directorio raíz del proyecto"
    exit 1
fi

print_success "Directorio del proyecto verificado"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    print_error "Python3 no está instalado"
    exit 1
fi

print_success "Python3 encontrado: $(python3 --version)"

# Crear archivos de log
mkdir -p logs
BACKEND_LOG="logs/backend.log"
FRONTEND_LOG="logs/frontend.log"

# Limpiar logs anteriores
> "$BACKEND_LOG"
> "$FRONTEND_LOG"

print_info "Logs creados en: logs/"

# Función para limpiar procesos al salir
cleanup() {
    print_warning "Deteniendo servicios..."
    
    # Matar procesos por PID si existen
    if [ ! -z "$BACKEND_PID" ] && ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_info "Deteniendo backend (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ] && ps -p $FRONTEND_PID > /dev/null 2>&1; then
        print_info "Deteniendo frontend (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Matar procesos por puerto como backup
    print_info "Limpiando puertos..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    
    print_success "Servicios detenidos"
    exit 0
}

# Configurar trap para limpiar al salir
trap cleanup EXIT INT TERM

# Verificar e instalar dependencias
print_status "Verificando dependencias..."

if [ ! -d "venv" ]; then
    print_info "Creando entorno virtual..."
    python3 -m venv venv
fi

print_info "Activando entorno virtual..."
source venv/bin/activate

print_info "Instalando/actualizando dependencias..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

print_success "Dependencias instaladas"

# Verificar que Streamlit esté instalado
if ! command -v streamlit &> /dev/null; then
    print_error "Streamlit no está instalado correctamente"
    exit 1
fi

print_success "Streamlit encontrado: $(streamlit --version)"

# Verificar puertos
print_status "Verificando puertos..."

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Puerto 8000 ya está en uso. Liberando..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Puerto 8501 ya está en uso. Liberando..."
    lsof -ti:8501 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

print_success "Puertos disponibles"

# Inicializar base de datos
print_status "Inicializando base de datos..."
cd src
python3 -c "
from db.analisis_db import init_db
init_db()
print('Base de datos inicializada')
" 2>/dev/null || print_warning "La base de datos ya existe"
cd ..

print_success "Base de datos lista"

# Iniciar Backend
print_status "Iniciando backend FastAPI..."
cd fastapi_backend

# Verificar que el archivo main.py existe
if [ ! -f "main.py" ]; then
    print_error "No se encontró main.py en fastapi_backend/"
    exit 1
fi

# Iniciar backend en segundo plano
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "../$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cd ..

# Esperar a que el backend se inicie
print_info "Esperando a que el backend se inicie..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend iniciado correctamente en http://localhost:8000"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Timeout: El backend no se inició correctamente"
        print_error "Revisa el log: $BACKEND_LOG"
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo

# Iniciar Frontend
print_status "Iniciando frontend Streamlit..."
cd src

# Verificar que el archivo main.py existe
if [ ! -f "main.py" ]; then
    print_error "No se encontró main.py en src/"
    exit 1
fi

# Iniciar frontend en segundo plano
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > "../$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

cd ..

# Esperar a que el frontend se inicie
print_info "Esperando a que el frontend se inicie..."
for i in {1..30}; do
    if curl -s http://localhost:8501 > /dev/null 2>&1; then
        print_success "Frontend iniciado correctamente en http://localhost:8501"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Timeout: El frontend no se inició correctamente"
        print_error "Revisa el log: $FRONTEND_LOG"
        exit 1
    fi
    sleep 1
    echo -n "."
done
echo

# Información final
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     🎉 SISTEMA INICIADO                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
print_success "Backend FastAPI: http://localhost:8000"
print_success "Frontend Streamlit: http://localhost:8501"
print_success "Documentación API: http://localhost:8000/docs"
echo
print_info "PIDs de los procesos:"
print_info "  Backend: $BACKEND_PID"
print_info "  Frontend: $FRONTEND_PID"
echo
print_info "Logs disponibles en:"
print_info "  Backend: $BACKEND_LOG"
print_info "  Frontend: $FRONTEND_LOG"
echo
print_warning "Presiona Ctrl+C para detener ambos servicios"
echo

# Monitorear procesos
while true; do
    # Verificar que ambos procesos sigan corriendo
    if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_error "El backend se detuvo inesperadamente"
        print_error "Revisa el log: $BACKEND_LOG"
        exit 1
    fi
    
    if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
        print_error "El frontend se detuvo inesperadamente"
        print_error "Revisa el log: $FRONTEND_LOG"
        exit 1
    fi
    
    sleep 5
done
