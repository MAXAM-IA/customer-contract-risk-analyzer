#!/bin/bash

# Script de instalación y configuración para AI-CC-Risk-Analyzer
echo "🚀 Configurando AI-CC-Risk-Analyzer con integración LLM..."

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Por favor instala Python 3.8 o superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar configuración de API Key
echo "🔑 Verificando configuración..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Advertencia: GOOGLE_API_KEY no está configurada."
    echo "   Para usar la funcionalidad LLM, configura la variable de entorno:"
    echo "   export GOOGLE_API_KEY='tu_clave_de_api_aqui'"
    echo ""
    echo "   O crea un archivo .env en el directorio raíz con:"
    echo "   GOOGLE_API_KEY=tu_clave_de_api_aqui"
else
    echo "✅ GOOGLE_API_KEY configurada correctamente"
fi

echo ""
echo "🎉 Instalación completada!"
echo ""
echo "Para iniciar el sistema:"
echo "1. Backend (FastAPI): cd fastapi_backend && uvicorn main:app --reload"
echo "2. Frontend (Streamlit): streamlit run src/main.py"
echo ""
echo "El sistema estará disponible en:"
echo "- Backend API: http://localhost:8000"
echo "- Frontend: http://localhost:8501"
