# AI-CC-Risk-Analyzer 🤖⚖️

Sistema de análisis inteligente de contratos con detección automática de riesgos legales utilizando LLM (Gemini).

## 🚀 Características Principales

- **Análisis Multimodal**: Soporte para archivos PDF y texto plano
- **LLM Integrado**: Utiliza Google Gemini para análisis inteligente
- **Evaluación de Riesgo**: Clasificación automática (Alto/Medio/Bajo)
- **Interfaz Web**: Frontend en Streamlit con API FastAPI
- **Logging Detallado**: Seguimiento completo del proceso de análisis
- **Procesamiento Asíncrono**: Análisis en segundo plano con seguimiento en tiempo real

## 📋 Prerrequisitos

- Python 3.8 o superior
- Google API Key para Gemini
- Git

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone [repositorio]
cd ai-cc-risk-analyzer
```

### 2. Ejecutar script de instalación
```bash
./install.sh
```
O manualmente:
```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea un archivo `.env` en el directorio raíz:
```bash
cp .env.example .env
```

Edita el archivo `.env` y agrega tu Google API Key:
```env
GOOGLE_API_KEY=tu_clave_de_google_api_aqui
```

Para obtener una API Key:
1. Visita [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Crea una nueva API Key
3. Cópiala al archivo `.env`

### 4. Verificar instalación
```bash
python test_system.py
```

## 🎯 Uso

### Scripts de inicio rápido

#### Método 1: Scripts automatizados
```bash
# Iniciar backend
./start_backend.sh

# En otra terminal - iniciar frontend  
cd src && streamlit run main.py
```

#### Método 2: Manual
Terminal 1 - Backend:
```bash
cd fastapi_backend
uvicorn main:app --reload
```

Terminal 2 - Frontend:
```bash
streamlit run src/main.py
```

### Acceder al sistema
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **Documentación API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🧪 Pruebas del Sistema

### Prueba completa automatizada
```bash
# 1. Iniciar el backend en una terminal
./start_backend.sh

# 2. En otra terminal, ejecutar la prueba completa
python3 test_full_system.py
```

Esta prueba verifica:
- ✅ Conectividad del backend
- ✅ Health check del sistema
- ✅ Carga de archivo y análisis asíncrono
- ✅ Polling de estado (cada 3 segundos como el frontend)
- ✅ Procesamiento con LLM  
- ✅ Evaluación de riesgos

### Otras pruebas disponibles
```bash
# Probar solo el backend
python test_backend.py

# Probar solo el LLM
python test_system.py
```

### Subir y analizar documentos

1. **Nuevo Análisis**:
   - Accede a http://localhost:8501
   - Sube un archivo PDF o de texto
   - El sistema realizará análisis asíncrono con preguntas predefinidas
   - El frontend hace polling cada 3 segundos para mostrar el progreso
   - Monitorea el estado en tiempo real

2. **Ver Resultados**:
   - Resultados detallados por pregunta
   - Evaluación de riesgo automática (Alto/Medio/Bajo)
   - Respuestas generadas por LLM
   - Opciones de exportación

3. **Re-análisis**:
   - Modificar preguntas individuales  
   - Re-análisis global con preguntas editadas
   - Comparación de resultados

### Flujo técnico
1. Frontend sube archivo → Backend (`/analizar`)
2. Backend guarda archivo con extensión original
3. Worker inicia análisis asíncrono en segundo plano
4. Frontend consulta estado cada 3s (`/estado/{id}`)
5. Worker procesa cada pregunta con Gemini LLM
6. Sistema actualiza progreso granularmente
7. Frontend muestra resultados finales

## 📊 Estructura del Proyecto

```
ai-cc-risk-analyzer/
├── fastapi_backend/           # API Backend
│   ├── main.py               # Endpoints de la API
│   ├── worker.py             # Lógica de análisis LLM
│   ├── contratos/            # Archivos subidos
│   ├── progreso/             # Estados de análisis
│   └── preguntas-risk-analyzer.xlsx
├── src/                      # Frontend Streamlit
│   ├── main.py
│   ├── pages/
│   └── db/
├── requirements.txt          # Dependencias
├── test_system.py           # Script de verificación
├── install.sh               # Script de instalación
└── .env.example             # Plantilla de configuración
```

## 🔧 Configuración Avanzada

### Variables de entorno disponibles
```env
GOOGLE_API_KEY=tu_clave        # Requerida
LOG_LEVEL=INFO                 # Opcional
PORT=8000                      # Opcional
HOST=localhost                 # Opcional
```

### Logging
Los logs se guardan en:
- `fastapi_backend/analisis.log` (análisis detallado)
- Consola (logs en tiempo real)

### Personalizar preguntas
Edita el archivo `fastapi_backend/preguntas-risk-analyzer.xlsx` para modificar las preguntas de análisis.

## ✅ Validación del Sistema

### Verificación rápida
```bash
# Valida que todo esté configurado correctamente
python3 validate_system.py
```

Este script verifica:
- 📂 Archivos requeridos
- 🔐 Variables de entorno  
- 📦 Dependencias Python
- 📁 Estructura de directorios

### Flujo de validación completo
```bash
# 1. Validar configuración
python3 validate_system.py

# 2. Iniciar backend 
./start_backend.sh

# 3. Probar sistema completo
python3 test_full_system.py
```

## 🐛 Resolución de Problemas

### Problema: El análisis se cuelga
**Diagnóstico**: 
```bash
# Verificar logs del backend
tail -f fastapi_backend/analisis.log

# Verificar estado del sistema
curl http://localhost:8000/health
```
**Solución**: Verifica los logs en `analisis.log` y la consola para identificar el error específico.

### Problema: Error de API Key
```
❌ GOOGLE_API_KEY no está configurada
```
**Solución**: 
1. Ejecuta `python3 validate_system.py` para diagnóstico
2. Verifica que el archivo `.env` existe con el formato correcto
3. Confirma que la API Key es válida en [Google AI Studio](https://aistudio.google.com/app/apikey)
4. Reinicia el servidor

### Problema: Dependencias faltantes
**Solución**:
```bash
pip install -r requirements.txt
```

### Problema: Archivo de preguntas no encontrado
**Solución**: Verifica que `fastapi_backend/preguntas-risk-analyzer.xlsx` existe.

### Problema: Frontend no puede conectar al backend
**Verificar**:
```bash
# ¿Está el backend funcionando?
curl http://localhost:8000/health

# ¿Hay errores en los logs?
tail fastapi_backend/analisis.log
```

## 📝 API Endpoints

- `POST /analizar` - Iniciar nuevo análisis
- `GET /estado/{id}` - Consultar progreso
- `POST /reanalisar_pregunta/{id}/{num}` - Re-analizar pregunta individual
- `POST /reanalisar_global/{id}` - Re-analizar todas las preguntas
- `GET /health` - Estado del sistema

## 🔄 Actualizaciones Recientes

### v2.0 - Integración LLM
- ✅ Integración completa con Google Gemini
- ✅ Análisis multimodal (PDF + texto)
- ✅ Evaluación automática de riesgo
- ✅ Logging detallado
- ✅ Health checks
- ✅ Manejo mejorado de errores

## 📞 Soporte

Para problemas o preguntas:
1. Ejecuta `python test_system.py` para diagnóstico
2. Verifica los logs en `analisis.log`
3. Consulta la documentación de la API en `/docs`

## 🔐 Seguridad

- Las API Keys se manejan como variables de entorno
- Los archivos se almacenan localmente de forma temporal
- No se envía información sensible a logs públicos

---
*Sistema desarrollado para análisis automatizado de contratos con IA* 🤖⚖️
