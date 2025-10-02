import time
import json
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, Optional, List, Tuple, Any
import math
from numbers import Real
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
import base64
import os
from io import BytesIO
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger = logging.getLogger(__name__)
    logger.info("✅ Variables de entorno cargadas desde .env")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.info("⚠️  python-dotenv no instalado, usando variables de entorno del sistema")

# Configurar logging para worker
logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview").strip() or "2024-12-01-preview"


def _sanitize_azure_endpoint(raw_endpoint: str) -> str:
    """Normaliza el endpoint de Azure quitando rutas específicas de la API."""
    if not raw_endpoint:
        return raw_endpoint

    trimmed = raw_endpoint.strip().rstrip("/")
    lower = trimmed.lower()
    marker = "/openai/"
    idx = lower.find(marker)
    if idx != -1:
        return trimmed[:idx]
    return trimmed


def _get_azure_endpoint() -> str:
    return _sanitize_azure_endpoint(os.getenv("AZURE_OPENAI_ENDPOINT", ""))


def _calcular_total_paginas(pdf_bytes: bytes) -> Optional[int]:
    """Devuelve el número de páginas del documento PDF suministrado."""
    try:
        import PyPDF2

        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
        return len(pdf_reader.pages)
    except Exception as exc:  # pragma: no cover - se usa para logging informativo
        logger.warning(f"⚠️ No se pudo determinar el número de páginas del documento: {exc}")
        return None


def _extraer_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF en bloques por página."""
    try:
        import PyPDF2
    except ImportError as exc:
        raise RuntimeError("PyPDF2 es requerido para extraer texto de PDF") from exc

    texto_paginas: List[str] = []

    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
    for num_pagina, page in enumerate(pdf_reader.pages, start=1):
        try:
            texto = page.extract_text() or ""
        except Exception as pagina_error:  # pragma: no cover - logging informativo
            logger.warning(f"⚠️ Error extrayendo texto de página {num_pagina}: {pagina_error}")
            continue

        if texto.strip():
            texto_paginas.append(f"--- Página {num_pagina} ---\n{texto}")

    return "\n\n".join(texto_paginas).strip()


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, Real):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def _preparar_contexto_documentos(contratos_paths: List[Path]) -> Dict[str, Any]:
    """Carga los archivos del análisis y prepara el contexto para el LLM."""
    documentos_cargados = []
    total_paginas = 0

    for path in contratos_paths:
        with open(path, "rb") as f:
            contenido = f.read()

        extension = path.suffix.lower()
        texto = ""

        if extension == ".pdf":
            paginas = _calcular_total_paginas(contenido) or 0
            total_paginas += paginas
            texto_pdf = _extraer_texto_pdf(contenido)
            if texto_pdf:
                texto = f"--- Archivo {path.name} ---\n{texto_pdf}"
        elif extension in {".txt", ".md"}:
            try:
                texto_decodificado = contenido.decode("utf-8", errors="ignore")
                texto = f"--- Archivo {path.name} ---\n{texto_decodificado}"
            except Exception as e:
                logger.warning(f"⚠️ No se pudo decodificar el archivo de texto {path.name}: {e}")
        else:
            logger.warning(f"⚠️ Formato no soportado (%s), se omitirá del contexto textual", extension)

        documentos_cargados.append({
            "path": path,
            "name": path.name,
            "bytes": contenido,
            "extension": extension,
            "texto": texto,
        })

    pdf_documentos = [doc for doc in documentos_cargados if doc["extension"] == ".pdf"]
    doc_principal = pdf_documentos[0] if pdf_documentos else None

    texto_principal = doc_principal["texto"] if doc_principal and doc_principal.get("texto") else None

    archivos_pdf_adjuntos = [
        (doc["name"], doc["bytes"])
        for doc in pdf_documentos
        if doc is not doc_principal
    ]

    texto_contexto = "\n\n".join([
        doc["texto"]
        for doc in documentos_cargados
        if doc.get("texto") and doc is not doc_principal
    ]).strip() or None

    texto_total_fallback = "\n\n".join([
        doc["texto"] for doc in documentos_cargados if doc.get("texto")
    ]).strip() or None

    pdf_principal = (doc_principal["name"], doc_principal["bytes"]) if doc_principal else None

    documentos_info = []
    for doc in documentos_cargados:
        documentos_info.append({
            "nombre": doc["name"],
            "extension": doc["extension"],
            "paginas": _calcular_total_paginas(doc["bytes"]) if doc["extension"] == ".pdf" else None,
        })

    return {
        "documentos": documentos_cargados,
        "documentos_info": documentos_info,
        "total_paginas": total_paginas or None,
        "pdf_principal": pdf_principal,
        "texto_principal": texto_principal,
        "archivos_pdf_adjuntos": archivos_pdf_adjuntos,
        "texto_contexto": texto_contexto,
        "texto_fallback": texto_total_fallback,
    }


def _procesar_preguntas(
    preguntas: List[Dict[str, Any]],
    progreso_path: Path,
    contexto: Dict[str, Any],
    usar_adjuntos_pdf: bool,
    llm_metadata: Dict[str, str],
):
    base_data: Dict[str, Any] = {}
    if Path(progreso_path).exists():
        try:
            with open(progreso_path, "r", encoding="utf-8") as f:
                base_data = json.load(f) or {}
        except Exception:
            base_data = {}

    documentos_info = contexto.get("documentos_info") or base_data.get("documentos_info")

    total_paginas = contexto.get("total_paginas")
    if (not total_paginas) and documentos_info:
        paginas_sum = sum(
            doc.get("paginas", 0) or 0 for doc in documentos_info if isinstance(doc, dict)
        )
        total_paginas = paginas_sum or None

    progreso_data = {
        **base_data,
        "estado": "en_progreso",
        "progreso": 0,
        "total_preguntas": len(preguntas),
        "resultados": [],
        "fecha_inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
        "preguntas_originales": preguntas,
        "total_paginas": total_paginas,
        "modelo_llm": llm_metadata.get("modelo_llm"),
        "proveedor_llm": llm_metadata.get("proveedor_llm"),
        "usar_adjuntos_pdf": usar_adjuntos_pdf,
        "documentos_info": documentos_info,
    }

    with open(progreso_path, "w", encoding="utf-8") as f:
        json.dump(_sanitize_json(progreso_data), f, indent=2, ensure_ascii=False)
    logger.info("✅ Archivo de progreso inicializado")

    resultados = []
    documentos_cargados = contexto.get("documentos", [])

    for idx, pregunta_data in enumerate(preguntas):
        logger.info(f"📝 Procesando pregunta {idx + 1}/{len(preguntas)}")

        pregunta = pregunta_data.get("Pregunta", "")
        seccion = pregunta_data.get("Sección", "Sin sección")

        resultado = analizar_pregunta(
            pregunta,
            seccion,
            pdf_principal=contexto.get("pdf_principal"),
            texto_principal=contexto.get("texto_principal"),
            usar_adjuntos_pdf=usar_adjuntos_pdf,
            archivos_pdf_adjuntos=contexto.get("archivos_pdf_adjuntos"),
            texto_contexto=contexto.get("texto_contexto") or contexto.get("texto_fallback"),
        )

        resultado.update({
            "Pregunta": pregunta,
            "Sección": seccion,
        })

        resultados.append(resultado)

        progreso_data["progreso"] = idx + 1
        progreso_data["resultados"] = resultados
        progreso_data["fecha_modificacion"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(_sanitize_json(progreso_data), f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Pregunta {idx + 1} completada")

    progreso_data.update({
        "estado": "completado",
        "num_resultados": len(resultados),
        "fecha_finalizacion": time.strftime("%Y-%m-%d %H:%M:%S"),
    })

    with open(progreso_path, "w", encoding="utf-8") as f:
        json.dump(_sanitize_json(progreso_data), f, indent=2, ensure_ascii=False)

    logger.info(f"🎉 ANÁLISIS COMPLETADO EXITOSAMENTE - {len(resultados)} preguntas procesadas")


def _obtener_metadata_llm() -> Dict[str, str]:
    """Obtiene información básica del LLM configurado en el entorno."""
    azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "").strip()
    azure_endpoint = _get_azure_endpoint()
    azure_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()

    if azure_deployment and azure_endpoint and azure_key:
        return {
            "modelo_llm": azure_deployment,
            "proveedor_llm": "Azure OpenAI"
        }

    google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if google_api_key:
        return {
            "modelo_llm": DEFAULT_GEMINI_MODEL,
            "proveedor_llm": "Google Gemini"
        }

    return {
        "modelo_llm": "No configurado",
        "proveedor_llm": "Desconocido"
    }


def _crear_llm_chat() -> AzureChatOpenAI:
    """Crea una instancia del modelo configurado para análisis de contratos."""
    azure_endpoint = _get_azure_endpoint()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "").strip()

    if not (azure_endpoint and api_key and azure_deployment):
        raise ValueError("Configuración de Azure OpenAI incompleta")

    logger.info(
        "🤖 Inicializando modelo Azure OpenAI",
        extra={
            "azure_deployment": azure_deployment,
            "azure_endpoint": azure_endpoint,
        },
    )

    return AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        azure_deployment=azure_deployment,
        api_version=AZURE_API_VERSION,
    )


def _normalizar_respuesta_llm(respuesta_llm: str) -> Dict[str, str]:
    """Extrae el texto sin la línea de riesgo y el nivel de riesgo informado."""
    riesgo = "Medio"  # Valor por defecto

    if "RISK:" in respuesta_llm.upper() or "RIESGO:" in respuesta_llm.upper():
        lineas = respuesta_llm.split('\n')
        for linea in lineas:
            linea_upper = linea.upper()
            if "RISK:" in linea_upper or "RIESGO:" in linea_upper:
                if any(word in linea_upper for word in ["HIGH", "ALTO"]):
                    riesgo = "Alto"
                elif any(word in linea_upper for word in ["LOW", "BAJO"]):
                    riesgo = "Bajo"
                elif any(word in linea_upper for word in ["MEDIUM", "MEDIO"]):
                    riesgo = "Medio"
                elif any(word in linea_upper for word in ["NOT EVALUATED", "NO EVALUADO", "SIN EVALUAR"]):
                    riesgo = "Sin evaluar"
                break

    lineas_respuesta = respuesta_llm.split('\n')
    respuesta_final = '\n'.join([
        linea for linea in lineas_respuesta
        if not any(word in linea.upper() for word in ["RISK:", "RIESGO:"])
    ]).strip()

    return {"Respuesta": respuesta_final, "Riesgo": riesgo}

def analizar_pregunta(
    pregunta: str,
    seccion: str,
    pdf_principal: Optional[Tuple[str, bytes]] = None,
    texto_principal: Optional[str] = None,
    usar_adjuntos_pdf: bool = False,
    archivos_pdf_adjuntos: Optional[List[Tuple[str, bytes]]] = None,
    texto_contexto: Optional[str] = None,
):
    """Analiza una pregunta combinando múltiples documentos como contexto."""
    archivos_pdf_adjuntos = archivos_pdf_adjuntos or []
    nombre_principal = pdf_principal[0] if pdf_principal else "N/A"

    logger.info(
        "🧠 ANALIZANDO PREGUNTA: '%s...' | Sección: %s | Documento principal: %s",
        pregunta[:50],
        seccion,
        nombre_principal,
    )

    try:
        adjuntos_disponibles: List[Tuple[str, bytes]] = []
        if pdf_principal:
            adjuntos_disponibles.append(pdf_principal)
        if archivos_pdf_adjuntos:
            adjuntos_disponibles.extend(archivos_pdf_adjuntos)

        if usar_adjuntos_pdf and adjuntos_disponibles:
            logger.info("📎 Enviando pregunta con %d adjunto(s) PDF al LLM", len(adjuntos_disponibles))
            try:
                return analizar_pregunta_con_adjuntos(pregunta, seccion, adjuntos_disponibles)
            except Exception as adjuntos_error:
                logger.warning(
                    "⚠️ Error utilizando adjuntos PDF, se intentará con texto plano: %s",
                    adjuntos_error,
                    exc_info=True,
                )

        texto_total = (texto_principal or "").strip()

        if not texto_total and pdf_principal:
            try:
                texto_total = _extraer_texto_pdf(pdf_principal[1])
            except Exception as e:
                logger.error(f"❌ Error extrayendo texto del PDF principal: {e}")

        if texto_contexto:
            texto_total = (f"{texto_total}\n\n{texto_contexto}" if texto_total else texto_contexto).strip()

        if texto_total:
            return analizar_pregunta_texto(pregunta, seccion, texto_total)

        logger.error("❌ No se pudo obtener contexto para la pregunta")
        return {
            "Respuesta": "No se pudo obtener contexto válido para analizar la pregunta",
            "Riesgo": "Alto",
        }

    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS: {str(e)}", exc_info=True)
        return {
            "Respuesta": f"Error al procesar la pregunta: {str(e)}",
            "Riesgo": "Alto"
        }


def analizar_pregunta_con_adjuntos(
    pregunta: str,
    seccion: str,
    archivos_pdf: List[Tuple[str, bytes]]
) -> Dict[str, str]:
    """Envía la pregunta al LLM adjuntando los PDFs codificados en base64."""
    logger.info(
        "📎 Preparando mensaje con adjuntos",
        extra={"pregunta_preview": pregunta[:80], "total_adjuntos": len(archivos_pdf)},
    )

    if not archivos_pdf:
        raise ValueError("Se requiere al menos un PDF para adjuntar")

    llm = _crear_llm_chat()

    system_prompt = """You are a legal assistant specialized in contract analysis. Answer the user's question clearly and precisely, using the attached document(s) as context.

Your answer must be written in Markdown format, suitable for inclusion in a DOCX document (use clear sections, bullet points, or numbered lists donde cada punto sea muy breve).

Haz la respuesta lo más concisa posible: máximo tres puntos o frases cortas y alrededor de 70 palabras en total.

Incluye únicamente los datos imprescindibles para justificar la respuesta, citando cláusulas, apartados o anexos relevantes cuando proceda.

Responde siempre en español neutro.

At the end of your answer, assess the legal risk level based on the following criteria:
- HIGH: Clauses that may create significant liabilities, unilateral termination, severe penalties, ambiguous terms favoring the other party, or lack of important protections.
- MEDIUM: Terms that require attention but do not pose immediate risks, standard clauses that could be improved.
- LOW: Favorable or neutral terms, standard industry clauses, or adequate protections.
- NOT EVALUATED: If you do not have enough information to assess the risk, or the question is not applicable, finish your answer with "RISK: NOT EVALUATED".

Finish your answer with a line that clearly states: "RISK: [HIGH/MEDIUM/LOW/NOT EVALUATED]"""  # noqa: E501

    input_text = (
        f"Section: {seccion}\n"
        f"Question: {pregunta}\n\n"
        "Please analyze the attached PDF contract(s) and answer the question."
    )

    human_content: List[Dict[str, str]] = [
        {
            "type": "text",
            "text": input_text,
        }
    ]

    for idx, (filename, contenido) in enumerate(archivos_pdf, start=1):
        nombre_archivo = filename or f"documento_{idx}.pdf"
        pdf_base64 = base64.b64encode(contenido).decode("utf-8")

        human_content.append(
            {
                "type": "file",
                "source_type": "base64",
                "data": pdf_base64,
                "mime_type": "application/pdf",
                "filename": nombre_archivo,
            }
        )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("user_messages"),
    ])

    human_message = HumanMessage(content=human_content)
    chain = prompt | llm | StrOutputParser()

    respuesta_llm = chain.invoke({
        "user_messages": [human_message],
    })

    logger.info(f"✅ Respuesta recibida con adjuntos (longitud: {len(respuesta_llm)} caracteres)")
    resultado = _normalizar_respuesta_llm(respuesta_llm)
    logger.info(f"🎯 Riesgo evaluado (adjuntos): {resultado['Riesgo']}")
    return resultado

def analizar_documento(contratos_paths, preguntas_path, progreso_path, usar_adjuntos_pdf=False):
    """Función principal que analiza un conjunto de documentos con todas las preguntas."""
    logger.info("🚀 INICIANDO ANÁLISIS ASÍNCRONO")
    logger.info(f"📁 Documentos: {contratos_paths}")
    logger.info(f"📋 Preguntas: {preguntas_path}")
    logger.info(f"📊 Progreso: {progreso_path}")

    try:
        contratos_paths = [Path(p) for p in contratos_paths]

        logger.info(f"📖 Leyendo preguntas desde: {preguntas_path}")
        df_preguntas = pd.read_excel(preguntas_path)
        df_preguntas = df_preguntas.where(pd.notnull(df_preguntas), None)
        preguntas = df_preguntas.to_dict("records")
        logger.info(f"✅ {len(preguntas)} preguntas cargadas exitosamente")

        contexto = _preparar_contexto_documentos(contratos_paths)
        llm_metadata = _obtener_metadata_llm()

        _procesar_preguntas(
            preguntas,
            progreso_path,
            contexto,
            usar_adjuntos_pdf,
            llm_metadata,
        )

    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS: {str(e)}", exc_info=True)
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(_sanitize_json({
                    "estado": "error",
                    "resultados": [],
                    "error": str(e),
                    "fecha_error": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "usar_adjuntos_pdf": usar_adjuntos_pdf,
                }), f, indent=2, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")

def analizar_documento_con_preguntas_custom(
    contratos_paths,
    preguntas_custom,
    progreso_path,
    usar_adjuntos_pdf=False,
):
    """Analiza documentos con preguntas personalizadas proporcionadas por el usuario."""
    logger.info(f"🚀 INICIANDO ANÁLISIS CON PREGUNTAS CUSTOM - {len(preguntas_custom)} preguntas")

    try:
        contratos_paths = [Path(p) for p in contratos_paths]

        preguntas = [
            {
                "Pregunta": item.get("pregunta", ""),
                "Sección": item.get("seccion", "Sin sección"),
            }
            for item in preguntas_custom
        ]

        contexto = _preparar_contexto_documentos(contratos_paths)
        llm_metadata = _obtener_metadata_llm()

        _procesar_preguntas(
            preguntas,
            progreso_path,
            contexto,
            usar_adjuntos_pdf,
            llm_metadata,
        )

    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS CUSTOM: {str(e)}", exc_info=True)
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(_sanitize_json({
                    "estado": "error",
                    "resultados": [],
                    "error": str(e),
                    "fecha_error": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "usar_adjuntos_pdf": usar_adjuntos_pdf,
                }), f, indent=2, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")

def reanalizar_pregunta_individual_sobreescribir(contratos_paths, pregunta_data, progreso_path):
    """
    Re-analiza una pregunta individual SOBREESCRIBIENDO el análisis original.
    Actualiza únicamente la pregunta especificada en el análisis existente.
    """
    logger.info(f"🔄 INICIANDO RE-ANÁLISIS INDIVIDUAL (SOBREESCRIBIR) - Pregunta: {pregunta_data.get('num_pregunta')}")
    
    try:
        # Leer el progreso original
        with open(progreso_path, "r", encoding="utf-8") as f:
            progreso_original = json.load(f)

        # Obtener el número de pregunta a actualizar
        num_pregunta = pregunta_data.get("num_pregunta", 0)

        usar_adjuntos_pdf = progreso_original.get("usar_adjuntos_pdf", False)
        
        # Verificar que existe el resultado para esa pregunta
        if "resultados" not in progreso_original or len(progreso_original["resultados"]) <= num_pregunta:
            raise Exception(f"No existe resultado para la pregunta {num_pregunta}")

        contratos_paths = [Path(p) for p in contratos_paths]
        contexto = _preparar_contexto_documentos(contratos_paths)

        llm_metadata = _obtener_metadata_llm()
        progreso_original["modelo_llm"] = llm_metadata.get("modelo_llm")
        progreso_original["proveedor_llm"] = llm_metadata.get("proveedor_llm")
        progreso_original["total_paginas"] = contexto.get("total_paginas")

        progreso_original["documentos_info"] = contexto.get("documentos_info")

        resultado = analizar_pregunta(
            pregunta_data["pregunta"],
            pregunta_data.get("seccion", "Sin sección"),
            pdf_principal=contexto.get("pdf_principal"),
            texto_principal=contexto.get("texto_principal"),
            usar_adjuntos_pdf=usar_adjuntos_pdf,
            archivos_pdf_adjuntos=contexto.get("archivos_pdf_adjuntos"),
            texto_contexto=contexto.get("texto_contexto") or contexto.get("texto_fallback"),
        )
        
        # Actualizar solo la pregunta específica en los resultados
        progreso_original["resultados"][num_pregunta].update({
            "Pregunta": pregunta_data["pregunta"],
            "Sección": pregunta_data.get("seccion", "Sin sección"), 
            "Respuesta": resultado["Respuesta"],
            "Riesgo": resultado["Riesgo"],
            "reanalizado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_reanalisis": "individual"
        })
        
        # Actualizar metadatos del análisis
        progreso_original.update({
            "estado": "completado",
            "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ultima_pregunta_reanalizada": num_pregunta,
            "num_resultados": len(progreso_original["resultados"])
        })
        
        # Guardar el progreso actualizado
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(_sanitize_json(progreso_original), f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ RE-ANÁLISIS INDIVIDUAL (SOBREESCRIBIR) COMPLETADO - Pregunta {num_pregunta} actualizada")
        
    except Exception as e:
        logger.error(f"❌ ERROR EN RE-ANÁLISIS INDIVIDUAL (SOBREESCRIBIR): {str(e)}", exc_info=True)
        try:
            # Actualizar solo el estado de error sin perder los datos existentes
            with open(progreso_path, "r", encoding="utf-8") as f:
                progreso_actual = json.load(f)
            
            progreso_actual.update({
                "estado": "error",
                "error": f"Error en re-análisis individual: {str(e)}",
                "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(_sanitize_json(progreso_actual), f, indent=2, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")


def reanalizar_documento_global_sobreescribir(contratos_paths, preguntas_editadas, progreso_path):
    """
    Re-analiza todas las preguntas SOBREESCRIBIENDO el análisis original.
    Mantiene el mismo ID y archivo de progreso.
    """
    logger.info(f"🔄 INICIANDO RE-ANÁLISIS GLOBAL (SOBREESCRIBIR) - {len(preguntas_editadas)} preguntas")
    
    try:
        with open(progreso_path, "r", encoding="utf-8") as f:
            progreso_original = json.load(f)

        progreso_original.update({
            "estado": "reanalisis_en_progreso",
            "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_reanalisis": "global",
            "progreso": 0,
            "total_preguntas": len(preguntas_editadas),
        })

        progreso_original["resultados"] = []

        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(_sanitize_json(progreso_original), f, indent=2, ensure_ascii=False)

        contratos_paths = [Path(p) for p in contratos_paths]
        contexto = _preparar_contexto_documentos(contratos_paths)

        llm_metadata = _obtener_metadata_llm()
        progreso_original["modelo_llm"] = llm_metadata.get("modelo_llm")
        progreso_original["proveedor_llm"] = llm_metadata.get("proveedor_llm")
        progreso_original["total_paginas"] = contexto.get("total_paginas")
        progreso_original["documentos_info"] = contexto.get("documentos_info")

        usar_adjuntos_pdf = progreso_original.get("usar_adjuntos_pdf", False)

        preguntas = [
            {
                "Pregunta": item.get("pregunta", ""),
                "Sección": item.get("seccion", "Sin sección"),
            }
            for item in preguntas_editadas
        ]

        _procesar_preguntas(
            preguntas,
            progreso_path,
            contexto,
            usar_adjuntos_pdf,
            llm_metadata,
        )

        with open(progreso_path, "r", encoding="utf-8") as f:
            progreso_final = json.load(f)

        progreso_final["preguntas_originales"] = preguntas

        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(_sanitize_json(progreso_final), f, indent=2, ensure_ascii=False)

        logger.info(f"✅ RE-ANÁLISIS GLOBAL (SOBREESCRIBIR) COMPLETADO - {len(preguntas)} preguntas procesadas")
        
    except Exception as e:
        logger.error(f"❌ ERROR EN RE-ANÁLISIS GLOBAL (SOBREESCRIBIR): {str(e)}", exc_info=True)
        try:
            # Leer estado actual y actualizar con error
            with open(progreso_path, "r", encoding="utf-8") as f:
                progreso_actual = json.load(f)
            
            progreso_actual.update({
                "estado": "error",
                "error": f"Error en re-análisis global: {str(e)}",
                "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(_sanitize_json(progreso_actual), f, indent=2, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")

def analizar_pregunta_texto(pregunta, seccion, texto_contrato):
    """
    Analiza una pregunta usando Gemini LLM con texto plano como contexto.
    Usado para archivos que no son PDF.
    Devuelve un dict con 'Respuesta' y 'Riesgo'.
    """
    logger.info(f"📝 ANALIZANDO PREGUNTA CON TEXTO: '{pregunta[:50]}...' | Sección: {seccion}")
    
    try:
        llm = _crear_llm_chat()
        logger.info("✅ Modelo inicializado correctamente para análisis con texto plano")

        logger.info(f"📄 Preparando texto para análisis (longitud: {len(texto_contrato)} caracteres)")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a legal assistant specialized in contract analysis. Answer based only on the attached document.

Instructions:

Write in Markdown, suitable for DOCX.

Use clear headings and max 3 bullet points or short sentences.

Limit to ~70 words total.

Reference specific clauses/sections when possible.

Be concise, professional, neutral, and precise.

Risk Assessment:
At the end, assign a legal risk level:

HIGH – major liabilities, penalties, unilateral rights, missing protections.

MEDIUM – terms need attention but not critical.

LOW – neutral or protective terms.

NOT EVALUATED – insufficient info.

Final line:
RISK: [HIGH/MEDIUM/LOW/NOT EVALUATED]

Sample Answers
Termination Clause

Either party may terminate with 30 days’ notice (Clause 12.2).

No penalty or compensation for early exit.

Potential exposure to sudden termination.

RISK: HIGH

Payment Terms

Payment due within 45 days after invoice (Clause 5.1).

No interest defined for late payment.

Standard but enforcement could be weak.

RISK: MEDIUM

Confidentiality

Mutual non-disclosure obligations (Clause 8.3).

Duration: 2 years post-termination.

Adequate and aligned with industry standards.

RISK: LOW

Liability

Liability capped at total contract value (Clause 9.4).

Excludes gross negligence and willful misconduct.

Balanced and protective framework.

RISK: LOW
"""),
            ("human", f"""
            Section: {{seccion}}
            Question: {{pregunta}}
            Document to analyze:{{texto_contrato}}""")
        ])
        
        logger.info(f"📝 Enviando consulta al LLM...")
        chain = prompt | llm | StrOutputParser()
        respuesta_llm = chain.invoke({
            "seccion": seccion,
            "pregunta": pregunta,
            "texto_contrato": texto_contrato
        })
        logger.info(f"✅ Respuesta recibida del LLM (longitud: {len(respuesta_llm)} caracteres)")

        resultado = _normalizar_respuesta_llm(respuesta_llm)
        logger.info(f"🎯 Riesgo evaluado: {resultado['Riesgo']}")
        logger.info("✅ Análisis completado exitosamente")
        return resultado
        
    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS CON TEXTO: {str(e)}", exc_info=True)
        return {
            "Respuesta": f"Error al procesar la pregunta: {str(e)}",
            "Riesgo": "Alto"
        }
