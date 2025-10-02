from fastapi import FastAPI, UploadFile, BackgroundTasks, Request, Form, File
from fastapi.responses import JSONResponse
import uuid
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Any
from numbers import Real
import math


def _generar_nombre_default(nombres_archivos: List[str]) -> str:
    base = "Analisis"
    if nombres_archivos:
        primer_nombre = Path(nombres_archivos[0]).stem
        if primer_nombre:
            base = primer_nombre
    fecha_tag = datetime.now().strftime("%Y%m%d")
    return f"{base}_{fecha_tag}"


def _sanitize_json_for_response(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_json_for_response(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_for_response(item) for item in value]
    if isinstance(value, Real):
        if math.isnan(value) or math.isinf(value):
            return None
    return value

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
except ImportError:
    print("⚠️  python-dotenv no instalado, usando variables de entorno del sistema")

# Añadir el directorio actual al path de Python
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from worker import (
    analizar_documento, 
    analizar_pregunta, 
    analizar_documento_con_preguntas_custom, 
    analizar_pregunta_texto,
    reanalizar_pregunta_individual_sobreescribir,
    reanalizar_documento_global_sobreescribir
)
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))
from db.analisis_db import actualizar_resultados_analisis

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analisis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
PROGRESO_DIR = BASE_DIR / "progreso"
# Cambiar a usar el archivo de preguntas en src/docs/
PREGUNTAS_PATH = BASE_DIR.parent / "src" / "docs" / "preguntas-risk-analyzer.xlsx"
PROGRESO_DIR.mkdir(exist_ok=True)

logger.info(f"Sistema iniciado. BASE_DIR: {BASE_DIR}")
logger.info(f"PREGUNTAS_PATH: {PREGUNTAS_PATH}, existe: {PREGUNTAS_PATH.exists()}")


def _obtener_paths_contrato(id_analisis: str) -> List[Path]:
    """Recupera todos los archivos asociados a un análisis."""
    contratos_dir = BASE_DIR / "contratos"
    analisis_dir = contratos_dir / id_analisis

    if analisis_dir.exists() and analisis_dir.is_dir():
        return sorted([p for p in analisis_dir.iterdir() if p.is_file()])

    # Compatibilidad con análisis antiguos donde el contrato era un único archivo
    legacy_files = sorted(contratos_dir.glob(f"{id_analisis}*"))
    return [p for p in legacy_files if p.is_file()]

@app.post("/analizar")
async def iniciar_analisis(
    background_tasks: BackgroundTasks,
    use_pdf_attachments: bool = Form(False),
    analysis_name: str = Form(None),
    files: List[UploadFile] = File(None),
    file: UploadFile | None = File(None),
):
    uploads: List[UploadFile] = []
    if files:
        uploads.extend([f for f in files if f is not None])
    if file is not None:
        uploads.append(file)

    if not uploads:
        return JSONResponse(status_code=400, content={"error": "No se adjuntaron archivos para el análisis"})

    id_analisis = str(uuid.uuid4())
    nombres_archivos = [u.filename or f"documento_{idx+1}" for idx, u in enumerate(uploads)]
    logger.info(
        "🔥 INICIO ANÁLISIS - ID: %s, Archivos: %s",
        id_analisis,
        ", ".join(nombres_archivos),
    )

    try:
        contratos_dir = BASE_DIR / "contratos"
        contratos_dir.mkdir(exist_ok=True)

        analisis_dir = contratos_dir / id_analisis
        analisis_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Directorio del análisis creado: {analisis_dir}")

        stored_paths: List[Path] = []
        cleaned_names: List[str] = []

        for index, upload in enumerate(uploads, start=1):
            original_name = upload.filename or f"documento_{index}"
            safe_name = f"{index:02d}_{Path(original_name).name}"
            destino = analisis_dir / safe_name

            contenido = await upload.read()
            with open(destino, "wb") as f:
                f.write(contenido)

            logger.info(
                "💾 Archivo guardado: %s (%d bytes)",
                destino,
                len(contenido),
            )

            stored_paths.append(destino)
            cleaned_names.append(original_name)

        progreso_path = PROGRESO_DIR / f"{id_analisis}.json"
        logger.info(f"📊 Creando archivo de progreso: {progreso_path}")

        analysis_name = (analysis_name or "").strip()
        if not analysis_name:
            analysis_name = _generar_nombre_default(cleaned_names)

        logger.info(f"🆔 Nombre del análisis: {analysis_name}")

        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({
                "estado": "en_cola",
                "resultados": [],
                "archivos": cleaned_names,
                "nombre_analisis": analysis_name,
                "documentos_info": [
                    {
                        "nombre": name,
                        "extension": Path(name).suffix,
                        "paginas": None,
                    }
                    for name in cleaned_names
                ],
            }, f)
        logger.info("✅ Archivo de progreso inicializado")

        if not PREGUNTAS_PATH.exists():
            logger.error(f"❌ ARCHIVO DE PREGUNTAS NO ENCONTRADO: {PREGUNTAS_PATH}")
            return JSONResponse(status_code=500, content={"error": "Archivo de preguntas no encontrado"})

        logger.info("🚀 Lanzando análisis en segundo plano con %d archivo(s)...", len(stored_paths))
        background_tasks.add_task(
            analizar_documento,
            stored_paths,
            PREGUNTAS_PATH,
            progreso_path,
            use_pdf_attachments,
        )

        return {
            "id": id_analisis,
            "archivos": cleaned_names,
             "nombre_analisis": analysis_name,
            "use_pdf_attachments": use_pdf_attachments,
        }

    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS {id_analisis}: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Error al procesar archivo: {str(e)}"})

@app.get("/procesos")
def listar_procesos():
    """Lista todos los procesos de análisis disponibles"""
    logger.info("📋 Listando todos los procesos disponibles")
    
    try:
        procesos = []
        
        # Recorrer todos los archivos .json en el directorio de progreso
        for archivo_progreso in PROGRESO_DIR.glob("*.json"):
            try:
                with open(archivo_progreso, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Agregar información del proceso
                proceso_info = {
                    "archivo": archivo_progreso.name,
                    "id": archivo_progreso.stem,
                    "estado": data.get("estado", "desconocido"),
                    "fecha_modificacion": datetime.fromtimestamp(archivo_progreso.stat().st_mtime).isoformat(),
                    "nombre_analisis": data.get("nombre_analisis"),
                }
                
                # Agregar información adicional si está disponible
                if "resultados" in data:
                    proceso_info["num_resultados"] = len(data["resultados"])
                
                if "preguntas_originales" in data:
                    proceso_info["num_preguntas"] = len(data["preguntas_originales"])
                
                if "mensaje" in data:
                    proceso_info["mensaje"] = data["mensaje"]
                
                procesos.append(proceso_info)
                
            except Exception as e:
                logger.error(f"❌ Error al leer archivo {archivo_progreso}: {str(e)}")
                continue
        
        # Ordenar por fecha de modificación (más reciente primero)
        procesos.sort(key=lambda x: x["fecha_modificacion"], reverse=True)
        
        logger.info(f"✅ Encontrados {len(procesos)} procesos")
        return procesos
        
    except Exception as e:
        logger.error(f"❌ Error al listar procesos: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Error al listar procesos: {str(e)}"})

@app.get("/progreso/{id_analisis}")
def obtener_progreso(id_analisis: str):
    """Alias para /estado/{id_analisis} para compatibilidad"""
    return obtener_estado(id_analisis)

@app.get("/estado/{id_analisis}")
def obtener_estado(id_analisis: str):
    logger.info(f"🔍 Consultando estado del análisis: {id_analisis}")
    path = PROGRESO_DIR / f"{id_analisis}.json"
    if not path.exists():
        logger.warning(f"📂 Archivo de progreso no encontrado: {path}")
        return JSONResponse(status_code=200, content={"estado": "no_iniciado", "resultados": [], "porcentaje": 0})
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"📊 Estado actual: {data.get('estado', 'desconocido')}")
        
        # Si el archivo ya tiene el campo 'estado', lo devolvemos tal cual
        if isinstance(data, dict) and "estado" in data:
            # Calcular porcentaje explícitamente
            progreso = data.get("progreso", 0)
            total = data.get("total_preguntas", 1)
            porcentaje = round((progreso / total) * 100, 1) if total > 0 else 0
            
            # Añadir porcentaje al resultado
            data["porcentaje"] = porcentaje
            
            logger.info(f"📈 Progreso calculado: {progreso}/{total} = {porcentaje}%")
            return _sanitize_json_for_response(data)
            
        # Si es una lista, es el formato antiguo
        if isinstance(data, list):
            completado = all(row.get("Estado") == "✅ Completado" for row in data) and len(data) > 0
            return _sanitize_json_for_response({
                "estado": "completado" if completado else "en_progreso",
                "resultados": data,
                "porcentaje": 100 if completado else 0
            })
        # Si es un error
        if isinstance(data, dict) and "error" in data:
            return {"estado": "error", "resultados": [], "error": data["error"], "porcentaje": 0}
        return _sanitize_json_for_response({"estado": "en_progreso", "resultados": [], "porcentaje": 0})
        
    except Exception as e:
        logger.error(f"❌ Error al leer archivo de progreso {path}: {str(e)}")
        return JSONResponse(status_code=200, content={"estado": "error", "resultados": [], "error": "Archivo de progreso corrupto", "porcentaje": 0})

@app.post("/reanalisar_pregunta/{id_analisis}/{num_pregunta}")
async def reanalizar_pregunta(id_analisis: str, num_pregunta: int, request: Request, background_tasks: BackgroundTasks):
    """
    Re-analiza una pregunta individual de forma asíncrona SOBREESCRIBIENDO el análisis original.
    El proceso se ejecuta en background usando el mismo ID y progreso_path original.
    """
    data = await request.json()
    pregunta_modificada = data.get("pregunta") if data else None
    seccion_modificada = data.get("seccion") if data else None
    
    # Verificar que el análisis original existe
    original_path = PROGRESO_DIR / f"{id_analisis}.json"
    if not original_path.exists():
        return JSONResponse(status_code=404, content={"error": "No existe el análisis original"})
    
    # Leer el progreso original para obtener las preguntas
    with open(original_path, "r", encoding="utf-8") as f:
        progreso_original = json.load(f)
    
    # Obtener preguntas originales de distintas fuentes posibles
    preguntas_originales = None
    if "preguntas_originales" in progreso_original:
        preguntas_originales = progreso_original["preguntas_originales"]
    elif "resultados" in progreso_original and progreso_original["resultados"]:
        # Reconstruir preguntas desde resultados
        preguntas_originales = [
            {"Pregunta": r.get("Pregunta", ""), "Sección": r.get("Sección", "")}
            for r in progreso_original["resultados"]
        ]
    
    if not preguntas_originales or num_pregunta >= len(preguntas_originales):
        return JSONResponse(status_code=400, content={"error": "Pregunta no encontrada o índice fuera de rango"})
    
    # Usar la pregunta/sección modificada si se envía, si no la original
    pregunta_original = preguntas_originales[num_pregunta]
    pregunta = pregunta_modificada or pregunta_original.get("Pregunta", "")
    seccion = seccion_modificada or pregunta_original.get("Sección", "")
    
    # Verificar que el contrato original existe
    contrato_files = _obtener_paths_contrato(id_analisis)
    if not contrato_files:
        return JSONResponse(status_code=404, content={"error": "No existe el contrato original"})

    # NO crear nuevo ID, usar el mismo análisis original para sobreescribir
    # Actualizar estado a "reanalisis_en_progreso" para indicar que está re-procesándose
    progreso_original["estado"] = "reanalisis_en_progreso"
    progreso_original["fecha_modificacion"] = datetime.now().isoformat()
    progreso_original["tipo_reanalisis"] = f"individual_pregunta_{num_pregunta}"
    
    # Guardar estado actualizado
    with open(original_path, "w", encoding="utf-8") as f:
        json.dump(progreso_original, f, ensure_ascii=False, indent=2)
    
    # Preparar datos para el análisis individual
    pregunta_data = {
        "pregunta": pregunta,
        "seccion": seccion,
        "num_pregunta": num_pregunta  # Añadir el índice para saber qué pregunta actualizar
    }
    
    # Lanzar el re-análisis individual en segundo plano usando el MISMO archivo de progreso
    background_tasks.add_task(
        reanalizar_pregunta_individual_sobreescribir,
        contrato_files,
        pregunta_data,
        original_path,
    )
    
    logger.info(f"Re-análisis individual iniciado para pregunta {num_pregunta} del análisis {id_analisis}. SOBREESCRIBIENDO análisis original.")
    return {"id": id_analisis, "mensaje": "Re-análisis individual iniciado (sobreescribiendo análisis original)"}

@app.post("/reanalisar_global/{id_analisis}")
async def reanalizar_global(id_analisis: str, request: Request, background_tasks: BackgroundTasks):
    """
    Re-analiza todas las preguntas usando las preguntas editadas enviadas por el usuario.
    SOBREESCRIBE el análisis original con el mismo ID.
    """
    data = await request.json()
    preguntas_editadas = data.get("preguntas", [])
    
    # Verificar que el análisis original existe
    original_path = PROGRESO_DIR / f"{id_analisis}.json"
    if not original_path.exists():
        return JSONResponse(status_code=404, content={"error": "No existe el análisis original"})
    
    # Verificar que el contrato original existe
    contrato_files = _obtener_paths_contrato(id_analisis)
    if not contrato_files:
        return JSONResponse(status_code=404, content={"error": "No existe el contrato original"})

    # NO crear nuevo ID, usar el mismo análisis original para sobreescribir
    # Leer progreso original y actualizar estado
    with open(original_path, "r", encoding="utf-8") as f:
        progreso_original = json.load(f)
    
    # Actualizar estado a "reanalisis_en_progreso" para indicar que está re-procesándose
    progreso_original["estado"] = "reanalisis_en_progreso"
    progreso_original["fecha_modificacion"] = datetime.now().isoformat()
    progreso_original["tipo_reanalisis"] = "global"
    progreso_original["preguntas_editadas"] = preguntas_editadas
    
    # Guardar estado actualizado
    with open(original_path, "w", encoding="utf-8") as f:
        json.dump(progreso_original, f, ensure_ascii=False, indent=2)
    
    # Lanzar el análisis en segundo plano con las preguntas editadas USANDO EL MISMO archivo de progreso
    background_tasks.add_task(
        reanalizar_documento_global_sobreescribir,
        contrato_files,
        preguntas_editadas,
        original_path,
    )
    
    logger.info(f"Reanálisis global iniciado para {id_analisis}. SOBREESCRIBIENDO análisis original.")
    return {"id": id_analisis, "mensaje": "Reanálisis global iniciado (sobreescribiendo análisis original)"}

@app.get("/health")
def health_check():
    """Endpoint de salud para verificar que el sistema funciona"""
    logger.info("🏥 Health check solicitado")
    
    # Verificar componentes clave
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Verificar archivo de preguntas
    status["checks"]["preguntas_file"] = {
        "status": "ok" if PREGUNTAS_PATH.exists() else "error",
        "path": str(PREGUNTAS_PATH)
    }
    
    # Verificar directorios
    status["checks"]["directories"] = {
        "contratos": (BASE_DIR / "contratos").exists(),
        "progreso": (BASE_DIR / "progreso").exists()
    }
    
    # Verificar API key
    api_key = os.getenv("GOOGLE_API_KEY", "")
    status["checks"]["google_api_key"] = {
        "configured": bool(api_key),
        "length": len(api_key) if api_key else 0
    }
    
    # Verificar dependencias
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        status["checks"]["langchain_google_genai"] = "ok"
    except ImportError:
        status["checks"]["langchain_google_genai"] = "error"
    
    # Determinar estado general
    has_errors = any(
        check.get("status") == "error" if isinstance(check, dict) else not check 
        for check in status["checks"].values()
    )
    
    if has_errors or not api_key:
        status["status"] = "degraded"
    
    logger.info(f"✅ Health check completado: {status['status']}")
    return status

@app.delete("/proceso/{id_analisis}")
async def cancelar_proceso(id_analisis: str):
    """Cancela un proceso de análisis en curso"""
    logger.info(f"🛑 CANCELAR PROCESO - ID: {id_analisis}")
    
    try:
        # Verificar si el proceso existe
        progreso_path = PROGRESO_DIR / f"{id_analisis}.json"
        contrato_paths = _obtener_paths_contrato(id_analisis)
        contratos_dir = BASE_DIR / "contratos"
        analisis_dir = contratos_dir / id_analisis
        
        if not progreso_path.exists():
            logger.warning(f"⚠️ Proceso {id_analisis} no encontrado")
            return JSONResponse(
                status_code=404, 
                content={"error": f"Proceso {id_analisis} no encontrado"}
            )
        
        # Leer el estado actual del proceso
        try:
            with open(progreso_path, "r", encoding="utf-8") as f:
                progreso_data = json.load(f)
            estado_actual = progreso_data.get("estado", "desconocido")
            logger.info(f"📊 Estado actual del proceso: {estado_actual}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo leer el estado actual: {e}")
            estado_actual = "desconocido"
        
        # Verificar si ya está completado
        if estado_actual == "completado":
            logger.info(f"ℹ️ Proceso {id_analisis} ya está completado, no se puede cancelar")
            return JSONResponse(
                status_code=400,
                content={"error": "No se puede cancelar un proceso ya completado"}
            )
        
        # Eliminar archivo de progreso
        if progreso_path.exists():
            progreso_path.unlink()
            logger.info(f"🗑️ Archivo de progreso eliminado: {progreso_path}")
        
        # Eliminar archivo del contrato
        eliminados = []
        if analisis_dir.exists() and analisis_dir.is_dir():
            for archivo in analisis_dir.iterdir():
                try:
                    archivo.unlink()
                    eliminados.append(str(archivo))
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo eliminar {archivo}: {e}")
            try:
                analisis_dir.rmdir()
                logger.info(f"🗑️ Directorio de contratos eliminado: {analisis_dir}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo eliminar el directorio {analisis_dir}: {e}")
        else:
            for archivo in contrato_paths:
                if archivo.exists():
                    archivo.unlink()
                    eliminados.append(str(archivo))
                    logger.info(f"🗑️ Archivo de contrato eliminado: {archivo}")

        logger.info(f"✅ Proceso {id_analisis} cancelado exitosamente")
        
        return JSONResponse(content={
            "mensaje": f"Proceso {id_analisis} cancelado exitosamente",
            "id": id_analisis,
            "estado_anterior": estado_actual,
            "archivos_eliminados": {
                "progreso": str(progreso_path) if progreso_path.exists() else None,
                "contratos": eliminados,
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error al cancelar proceso {id_analisis}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500, 
            content={"error": f"Error interno al cancelar proceso: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Iniciando servidor FastAPI en puerto 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
