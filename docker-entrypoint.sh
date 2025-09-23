#!/bin/bash

# Función para imprimir con colores
print_status() {
    echo "[$(date +'%H:%M:%S')] $1"
}

print_success() {
    echo "[$(date +'%H:%M:%S')] ✅ $1"
}

print_error() {
    echo "[$(date +'%H:%M:%S')] ❌ $1"
}

# Función para limpiar procesos al salir
cleanup() {
    print_status "Deteniendo servicios..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

# Configurar trap para limpiar al salir
trap cleanup EXIT INT TERM

# Iniciar Backend
print_status "Iniciando backend FastAPI..."
cd fastapi_backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "../logs/backend.log" 2>&1 &
BACKEND_PID=$!
cd ..

# Esperar a que el backend se inicie
print_status "Esperando a que el backend se inicie..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend iniciado correctamente en http://localhost:8000"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Timeout: El backend no se inició correctamente"
        exit 1
    fi
    sleep 1
done

# Iniciar Frontend
print_status "Iniciando frontend Streamlit..."
cd src
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > "../logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar a que el frontend se inicie
print_status "Esperando a que el frontend se inicie..."
for i in {1..30}; do
    if curl -s http://localhost:8501 > /dev/null 2>&1; then
        print_success "Frontend iniciado correctamente en http://localhost:8501"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Timeout: El frontend no se inició correctamente"
        exit 1
    fi
    sleep 1
done

print_success "Sistema completamente iniciado"
print_success "Backend FastAPI: http://localhost:8000"
print_success "Frontend Streamlit: http://localhost:8501"
print_success "Documentación API: http://localhost:8000/docs"

# Monitorear procesos
while true; do
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "El backend se detuvo inesperadamente"
        exit 1
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "El frontend se detuvo inesperadamente"
        exit 1
    fi
    
    sleep 5
done