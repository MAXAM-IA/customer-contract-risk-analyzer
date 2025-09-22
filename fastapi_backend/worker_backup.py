import time
import json
import pandas as pd
from pathlib import Path
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import base64
import httpx
import os

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

def analizar_pregunta(pregunta, seccion, pdf_bytes, pdf_filename="documento.pdf"):
    """
    Analiza una pregunta usando Gemini LLM y adjunta el PDF (en bytes) como contexto multimodal.
    Devuelve un dict con 'Respuesta' y 'Riesgo'.
    """
    logger.info(f"🧠 ANALIZANDO PREGUNTA: '{pregunta[:50]}...' | Sección: {seccion} | Archivo: {pdf_filename}")
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            logger.error("❌ GOOGLE_API_KEY no está configurada")
            return {
                "Respuesta": "Error: GOOGLE_API_KEY no configurada",
                "Riesgo": "Alto"
            }
        
        logger.info(f"🔑 API Key configurada correctamente")
        
        LLM_MODEL = "gemini-2.5-flash-preview-05-20"
        logger.info(f"🤖 Inicializando modelo: {LLM_MODEL}")
        
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            temperature=0,
            max_tokens=None,
            max_retries=2,
            http_client=httpx.Client(verify=False),
            google_api_key=api_key
        )
        logger.info(f"✅ Modelo inicializado correctamente")

        logger.info(f"📄 Convirtiendo PDF a base64 (tamaño: {len(pdf_bytes)} bytes)")
        base64_bytes = base64.b64encode(pdf_bytes)
        base64_string = base64_bytes.decode("utf-8")
        logger.info(f"✅ PDF convertido a base64 (tamaño: {len(base64_string)} caracteres)")

        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente legal experto en análisis de contratos. Responde de forma clara y precisa a la pregunta del usuario, usando el documento adjunto como contexto. 

Al final de tu respuesta, evalúa el nivel de riesgo legal basándote en los siguientes criterios:
- ALTO: Cláusulas que pueden generar responsabilidades significativas, terminación unilateral, penalizaciones severas, términos ambiguos que favorecen a la contraparte, ausencia de protecciones importantes.
- MEDIO: Términos que requieren atención pero no representan riesgos inmediatos, cláusulas estándar con posibles mejoras.
- BAJO: Términos favorables o neutros, cláusulas estándar de la industria, protecciones adecuadas.

Termina tu respuesta con una línea que indique claramente: "RIESGO: [ALTO/MEDIO/BAJO]" """),
            ("human", f"Sección: {seccion}\nPregunta: {pregunta}"),
            (
                "human",
                [
                    {
                        "type": "file",
                        "source_type": "base64",
                        "filename": pdf_filename,
                        "data": base64_string,
                        "mime_type": "application/pdf",
                    }
                ],
            )
        ])
        
        logger.info(f"📝 Enviando consulta al LLM...")
        chain = prompt | llm | StrOutputParser()
        respuesta_llm = chain.invoke({})
        logger.info(f"✅ Respuesta recibida del LLM (longitud: {len(respuesta_llm)} caracteres)")
        
        # Extraer el nivel de riesgo de la respuesta del LLM
        riesgo = "Medio"  # Valor por defecto
        if "RIESGO:" in respuesta_llm:
            lineas = respuesta_llm.split('\n')
            for linea in lineas:
                if "RIESGO:" in linea.upper():
                    if "ALTO" in linea.upper():
                        riesgo = "Alto"
                    elif "BAJO" in linea.upper():
                        riesgo = "Bajo"
                    elif "MEDIO" in linea.upper():
                        riesgo = "Medio"
                    break
        
        logger.info(f"🎯 Riesgo evaluado: {riesgo}")
        
        # Limpiar la respuesta removiendo la línea de riesgo para que no aparezca duplicada
        respuesta_limpia = respuesta_llm
        if "RIESGO:" in respuesta_llm:
            lineas = respuesta_llm.split('\n')
            lineas_filtradas = [linea for linea in lineas if not linea.upper().startswith("RIESGO:")]
            respuesta_limpia = '\n'.join(lineas_filtradas).strip()
        
        logger.info(f"✅ Análisis completado exitosamente")
        return {
            "Respuesta": respuesta_limpia,
            "Riesgo": riesgo
        }
        
    except Exception as e:
        logger.error(f"❌ ERROR al analizar pregunta: {str(e)}", exc_info=True)
        return {
            "Respuesta": f"Error al analizar la pregunta: {str(e)}",
            "Riesgo": "Alto"
        }

def pdf_file_to_base64_string(filepath):
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()
        base64_bytes = base64.b64encode(pdf_bytes)
        base64_string = base64_bytes.decode("utf-8")
        return base64_string

def analizar_pregunta_llm(pregunta, seccion, pdf_path):
    """
    Analiza una pregunta usando Gemini LLM y adjunta el PDF como contexto.
    Devuelve un dict con 'Respuesta' y 'Riesgo' (demo: riesgo bajo si no se menciona 'terminate').
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    LLM_MODEL = "gemini-2.5-flash-preview-05-20"
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        temperature=0,
        max_tokens=None,
        max_retries=2,
        http_client=httpx.Client(verify=False),
        google_api_key=api_key
    )

    pdf_data = pdf_file_to_base64_string(pdf_path)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un asistente legal experto en análisis de contratos. Responde de forma clara y precisa a la pregunta del usuario, usando el documento adjunto como contexto. Si la pregunta implica un riesgo legal relevante, indícalo."),
        ("human", f"Sección: {seccion}\nPregunta: {pregunta}"),
        (
            "human",
            [
                {
                    "type": "file",
                    "source_type": "base64",
                    "filename": os.path.basename(pdf_path),
                    "data": pdf_data,
                    "mime_type": "application/pdf",
                }
            ],
        )
    ])
    chain = prompt | llm | StrOutputParser()
    respuesta_llm = chain.invoke({})
    riesgo = "Alto" if "terminate" in pregunta.lower() else "Bajo"
    return {
        "Respuesta": respuesta_llm,
        "Riesgo": riesgo
    }

def analizar_documento(contrato_path, preguntas_path, progreso_path):
    logger.info(f"🚀 INICIANDO ANÁLISIS DE DOCUMENTO EN SEGUNDO PLANO")
    logger.info(f"📄 Contrato: {contrato_path}")
    logger.info(f"❓ Preguntas: {preguntas_path}")
    logger.info(f"📊 Progreso: {progreso_path}")
    
    contrato_path = Path(contrato_path)
    
    # Actualizar estado inmediatamente a "iniciando"
    try:
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({
                "estado": "iniciando", 
                "resultados": [], 
                "mensaje": "Iniciando análisis del documento..."
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"� Estado inicial guardado: 'iniciando'")
    except Exception as e:
        logger.error(f"❌ Error guardando estado inicial: {str(e)}")
    
    try:
        logger.info(f"�📖 Leyendo archivo de contrato...")
        # Leer el archivo según su extensión
        if contrato_path.suffix.lower() == '.pdf':
            logger.info(f"🔍 Archivo detectado como PDF")
            with open(contrato_path, "rb") as f:
                pdf_bytes = f.read()
            usar_pdf = True
            logger.info(f"✅ PDF leído exitosamente ({len(pdf_bytes)} bytes)")
        else:
            logger.info(f"🔍 Archivo detectado como texto ({contrato_path.suffix})")
            # Para archivos de texto, leer como texto
            with open(contrato_path, "r", encoding="utf-8", errors="replace") as f:
                texto_contrato = f.read()
            usar_pdf = False
            logger.info(f"✅ Texto leído exitosamente ({len(texto_contrato)} caracteres)")
    except Exception as e:
        logger.error(f"❌ ERROR leyendo contrato: {str(e)}")
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({"estado": "error", "resultados": [], "error": f"Error leyendo contrato: {str(e)}"}, f, ensure_ascii=False, indent=2)
        return

    # Actualizar estado a "leyendo preguntas"
    try:
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({
                "estado": "en_progreso", 
                "resultados": [], 
                "mensaje": "Leyendo archivo de preguntas..."
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ Error actualizando estado: {str(e)}")

    try:
        logger.info(f"📋 Leyendo archivo de preguntas...")
        preguntas_df = pd.read_excel(preguntas_path)
        logger.info(f"✅ Archivo de preguntas leído exitosamente ({len(preguntas_df)} preguntas)")
    except Exception as e:
        logger.error(f"❌ ERROR leyendo preguntas: {str(e)}")
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({"estado": "error", "resultados": [], "error": f"Error leyendo preguntas: {str(e)}"}, f, ensure_ascii=False, indent=2)
        return

    resultados = []
    preguntas_originales = []
    
    logger.info(f"🔄 Procesando preguntas iniciales...")
    for idx, row in preguntas_df.iterrows():
        numero = row.get("Número de Pregunta") or row.get("Numero de Pregunta") or row.get("Nº de Pregunta") or ""
        pregunta = row.get("Pregunta") or ""
        seccion = row.get("Sección") or row.get("Seccion") or ""
        preguntas_originales.append({
            "Número": numero,
            "Pregunta": pregunta,
            "Sección": seccion
        })
    
    logger.info(f"✅ {len(preguntas_originales)} preguntas procesadas")
    
    # Guardar estado inicial con preguntas originales
    logger.info(f"💾 Guardando estado inicial con preguntas...")
    with open(progreso_path, "w", encoding="utf-8") as f:
        json.dump({
            "estado": "en_progreso", 
            "preguntas_originales": preguntas_originales, 
            "resultados": resultados,
            "mensaje": f"Preparando análisis de {len(preguntas_originales)} preguntas..."
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"🎯 COMENZANDO ANÁLISIS DE PREGUNTAS...")
    for idx, row in preguntas_df.iterrows():
        numero = row.get("Número de Pregunta") or row.get("Numero de Pregunta") or row.get("Nº de Pregunta") or ""
        pregunta = row.get("Pregunta") or ""
        seccion = row.get("Sección") or row.get("Seccion") or ""
        
        logger.info(f"🔍 PREGUNTA {idx+1}/{len(preguntas_df)} - {numero}: '{pregunta[:50]}...'")
        
        # Actualizar estado con pregunta actual
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump({
                    "estado": "en_progreso", 
                    "preguntas_originales": preguntas_originales, 
                    "resultados": resultados,
                    "mensaje": f"Analizando pregunta {idx+1}/{len(preguntas_df)}: {pregunta[:30]}..."
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Error actualizando progreso pregunta {idx+1}: {str(e)}")
        
        # Usar la función apropiada según el tipo de archivo
        try:
            if usar_pdf:
                logger.info(f"📄 Analizando con función PDF...")
                salida = analizar_pregunta(pregunta, seccion, pdf_bytes, contrato_path.name)
            else:
                logger.info(f"📝 Analizando con función texto...")
                salida = analizar_pregunta_texto(pregunta, seccion, texto_contrato)
            
            logger.info(f"✅ Pregunta {idx+1} completada - Riesgo: {salida['Riesgo']}")
        except Exception as e:
            logger.error(f"❌ ERROR en pregunta {idx+1}: {str(e)}")
            salida = {
                "Respuesta": f"Error al procesar la pregunta: {str(e)}",
                "Riesgo": "Alto"
            }
            
        resultados.append({
            "Número": numero,
            "Pregunta": pregunta,
            "Sección": seccion,
            "Estado": "✅ Completado",
            "Respuesta": salida["Respuesta"],
            "Riesgo": salida["Riesgo"]
        })
        
        # Actualizar progreso después de cada pregunta
        logger.info(f"💾 Actualizando progreso ({idx+1}/{len(preguntas_df)})...")
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump({
                    "estado": "en_progreso", 
                    "preguntas_originales": preguntas_originales, 
                    "resultados": resultados,
                    "mensaje": f"Completadas {len(resultados)}/{len(preguntas_originales)} preguntas"
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Error guardando progreso: {str(e)}")

    logger.info(f"🎉 ANÁLISIS COMPLETADO - {len(resultados)} preguntas procesadas")
    try:
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({
                "estado": "completado", 
                "preguntas_originales": preguntas_originales, 
                "resultados": resultados,
                "mensaje": f"Análisis completado exitosamente - {len(resultados)} preguntas procesadas"
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Estado final guardado en {progreso_path}")
    except Exception as e:
        logger.error(f"❌ Error guardando estado final: {str(e)}")

def analizar_documento_con_preguntas_custom(contrato_path, preguntas_custom, progreso_path):
    """
    Analiza un documento con preguntas personalizadas (para reanálisis global).
    """
    contrato_path = Path(contrato_path)
    
    try:
        # Leer el archivo según su extensión
        if contrato_path.suffix.lower() == '.pdf':
            with open(contrato_path, "rb") as f:
                pdf_bytes = f.read()
            usar_pdf = True
        else:
            # Para archivos de texto, leer como texto
            with open(contrato_path, "r", encoding="utf-8", errors="replace") as f:
                texto_contrato = f.read()
            usar_pdf = False
    except Exception as e:
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({"estado": "error", "resultados": [], "error": f"Error leyendo contrato: {str(e)}"}, f, ensure_ascii=False, indent=2)
        return

    resultados = []
    preguntas_originales = []
    
    # Usar las preguntas personalizadas
    for pregunta_data in preguntas_custom:
        preguntas_originales.append({
            "Número": pregunta_data.get("numero", ""),
            "Pregunta": pregunta_data.get("pregunta", ""),
            "Sección": pregunta_data.get("seccion", "")
        })
    
    # Guardar estado inicial con preguntas originales
    with open(progreso_path, "w", encoding="utf-8") as f:
        json.dump({"estado": "en_progreso", "preguntas_originales": preguntas_originales, "resultados": resultados}, f, ensure_ascii=False, indent=2)

    for idx, pregunta_data in enumerate(preguntas_custom):
        numero = pregunta_data.get("numero", "")
        pregunta = pregunta_data.get("pregunta", "")
        seccion = pregunta_data.get("seccion", "")
        
        # Usar la función apropiada según el tipo de archivo
        if usar_pdf:
            salida = analizar_pregunta(pregunta, seccion, pdf_bytes, contrato_path.name)
        else:
            salida = analizar_pregunta_texto(pregunta, seccion, texto_contrato)
            
        resultados.append({
            "Número": numero,
            "Pregunta": pregunta,
            "Sección": seccion,
            "Estado": "✅ Completado",
            "Respuesta": salida["Respuesta"],
            "Riesgo": salida["Riesgo"]
        })
        
        # Actualizar progreso después de cada pregunta
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump({"estado": "en_progreso", "preguntas_originales": preguntas_originales, "resultados": resultados}, f, ensure_ascii=False, indent=2)

    # Marcar como completado
    with open(progreso_path, "w", encoding="utf-8") as f:
        json.dump({"estado": "completado", "preguntas_originales": preguntas_originales, "resultados": resultados}, f, ensure_ascii=False, indent=2)

def analizar_pregunta_texto(pregunta, seccion, texto_contrato):
    """
    Analiza una pregunta usando Gemini LLM con texto plano como contexto.
    Usado para archivos que no son PDF.
    Devuelve un dict con 'Respuesta' y 'Riesgo'.
    """
    logger.info(f"📝 ANALIZANDO PREGUNTA CON TEXTO: '{pregunta[:50]}...' | Sección: {seccion}")
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            logger.error("❌ GOOGLE_API_KEY no está configurada")
            return {
                "Respuesta": "Error: GOOGLE_API_KEY no configurada",
                "Riesgo": "Alto"
            }
        
        logger.info(f"🔑 API Key configurada correctamente")
        
        LLM_MODEL = "gemini-2.5-flash-preview-05-20"
        logger.info(f"🤖 Inicializando modelo: {LLM_MODEL}")
        
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            temperature=0,
            max_tokens=None,
            max_retries=2,
            http_client=httpx.Client(verify=False),
            google_api_key=api_key
        )
        logger.info(f"✅ Modelo inicializado correctamente")

        logger.info(f"📄 Preparando texto para análisis (longitud: {len(texto_contrato)} caracteres)")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente legal experto en análisis de contratos. Responde de forma clara y precisa a la pregunta del usuario, usando el documento adjunto como contexto. 

Al final de tu respuesta, evalúa el nivel de riesgo legal basándote en los siguientes criterios:
- ALTO: Cláusulas que pueden generar responsabilidades significativas, terminación unilateral, penalizaciones severas, términos ambiguos que favorecen a la contraparte, ausencia de protecciones importantes.
- MEDIO: Términos que requieren atención pero no representan riesgos inmediatos, cláusulas estándar con posibles mejoras.
- BAJO: Términos favorables o neutros, cláusulas estándar de la industria, protecciones adecuadas.

Termina tu respuesta con una línea que indique claramente: "RIESGO: [ALTO/MEDIO/BAJO]" """),
            ("human", f"Sección: {seccion}\nPregunta: {pregunta}\n\nDocumento a analizar:\n{texto_contrato}")
        ])
        
        logger.info(f"📝 Enviando consulta al LLM...")
        chain = prompt | llm | StrOutputParser()
        respuesta_llm = chain.invoke({})
        logger.info(f"✅ Respuesta recibida del LLM (longitud: {len(respuesta_llm)} caracteres)")
        
        # Extraer el nivel de riesgo de la respuesta del LLM
        riesgo = "Medio"  # Valor por defecto
        if "RIESGO:" in respuesta_llm:
            lineas = respuesta_llm.split('\n')
            for linea in lineas:
                if "RIESGO:" in linea.upper():
                    if "ALTO" in linea.upper():
                        riesgo = "Alto"
                    elif "BAJO" in linea.upper():
                        riesgo = "Bajo"
                    elif "MEDIO" in linea.upper():
                        riesgo = "Medio"
                    break
        
        logger.info(f"🎯 Riesgo evaluado: {riesgo}")
        
        # Limpiar la respuesta removiendo la línea de riesgo para que no aparezca duplicada
        respuesta_limpia = respuesta_llm
