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
    Analiza una pregunta usando Gemini LLM extrayendo texto del PDF como contexto.
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

        # Extraer texto del PDF usando PyPDF2
        try:
            import PyPDF2
            from io import BytesIO
            
            logger.info(f"📄 Extrayendo texto del PDF (tamaño: {len(pdf_bytes)} bytes)")
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            texto_completo = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    texto_pagina = page.extract_text()
                    texto_completo += f"\n--- Página {page_num + 1} ---\n{texto_pagina}\n"
                except Exception as e:
                    logger.warning(f"⚠️ Error extrayendo texto de página {page_num + 1}: {e}")
                    continue
            
            logger.info(f"✅ Texto extraído: {len(texto_completo)} caracteres")
            
            if not texto_completo.strip():
                raise Exception("No se pudo extraer texto del PDF")
                
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto del PDF: {e}")
            return {
                "Respuesta": f"Error al extraer texto del PDF: {str(e)}",
                "Riesgo": "Alto"
            }
        
        # Ahora usar la función analizar_pregunta_texto con el texto extraído
        return analizar_pregunta_texto(pregunta, seccion, texto_completo)
        
    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS: {str(e)}", exc_info=True)
        return {
            "Respuesta": f"Error al procesar la pregunta: {str(e)}",
            "Riesgo": "Alto"
        }

def analizar_documento(contrato_path, preguntas_path, progreso_path):
    """Función principal que analiza un documento con todas las preguntas de manera asíncrona"""
    logger.info(f"🚀 INICIANDO ANÁLISIS ASÍNCRONO")
    logger.info(f"📁 Contrato: {contrato_path}")
    logger.info(f"📋 Preguntas: {preguntas_path}")
    logger.info(f"📊 Progreso: {progreso_path}")
    
    try:
        # Leer las preguntas del archivo Excel
        logger.info(f"📖 Leyendo preguntas desde: {preguntas_path}")
        df_preguntas = pd.read_excel(preguntas_path)
        preguntas = df_preguntas.to_dict('records')
        logger.info(f"✅ {len(preguntas)} preguntas cargadas exitosamente")
        
        # Leer el PDF del contrato
        logger.info(f"📄 Leyendo contrato desde: {contrato_path}")
        with open(contrato_path, "rb") as f:
            pdf_bytes = f.read()
        logger.info(f"✅ Contrato leído exitosamente ({len(pdf_bytes)} bytes)")
        
        # Inicializar el archivo de progreso
        logger.info(f"📊 Inicializando archivo de progreso")
        progreso_data = {
            "estado": "en_progreso",
            "progreso": 0,
            "total_preguntas": len(preguntas),
            "resultados": [],
            "fecha_inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
            "preguntas_originales": preguntas
        }
        
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Archivo de progreso inicializado")
        
        # Procesar cada pregunta
        resultados = []
        for idx, pregunta_data in enumerate(preguntas):
            logger.info(f"📝 Procesando pregunta {idx+1}/{len(preguntas)}")
            
            pregunta = pregunta_data.get("Pregunta", "")
            seccion = pregunta_data.get("Sección", "Sin sección")
            
            # Analizar la pregunta
            resultado = analizar_pregunta(pregunta, seccion, pdf_bytes, contrato_path.name)
            
            # Añadir información de la pregunta al resultado
            resultado.update({
                "Pregunta": pregunta,
                "Sección": seccion,
            })
            
            resultados.append(resultado)
            
            # Actualizar progreso
            progreso_data["progreso"] = idx + 1
            progreso_data["resultados"] = resultados
            progreso_data["fecha_modificacion"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(progreso_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Pregunta {idx+1} completada")
        
        # Finalizar el análisis
        progreso_data["estado"] = "completado"
        progreso_data["num_resultados"] = len(resultados)
        progreso_data["fecha_finalizacion"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"🎉 ANÁLISIS COMPLETADO EXITOSAMENTE - {len(resultados)} preguntas procesadas")
        
    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS: {str(e)}", exc_info=True)
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump({
                    "estado": "error",
                    "resultados": [],
                    "error": str(e),
                    "fecha_error": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")

def analizar_documento_con_preguntas_custom(contrato_path, preguntas_custom, progreso_path):
    """Analiza un documento con preguntas personalizadas proporcionadas por el usuario"""
    logger.info(f"🚀 INICIANDO ANÁLISIS CON PREGUNTAS CUSTOM - {len(preguntas_custom)} preguntas")
    
    try:
        # Leer el PDF del contrato
        with open(contrato_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Inicializar el archivo de progreso
        progreso_data = {
            "estado": "en_progreso",
            "progreso": 0,
            "total_preguntas": len(preguntas_custom),
            "resultados": [],
            "fecha_inicio": time.strftime("%Y-%m-%d %H:%M:%S"),
            "preguntas_originales": preguntas_custom
        }
        
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_data, f, indent=2, ensure_ascii=False)
        
        # Procesar cada pregunta
        resultados = []
        for idx, pregunta_data in enumerate(preguntas_custom):
            logger.info(f"📝 Procesando pregunta custom {idx+1}/{len(preguntas_custom)}")
            
            pregunta = pregunta_data.get("pregunta", "")
            seccion = pregunta_data.get("seccion", "Sin sección")
            
            # Analizar la pregunta
            resultado = analizar_pregunta(pregunta, seccion, pdf_bytes, contrato_path.name)
            
            # Añadir información de la pregunta al resultado
            resultado.update({
                "Pregunta": pregunta,
                "Sección": seccion,
            })
            
            resultados.append(resultado)
            
            # Actualizar progreso
            progreso_data["progreso"] = idx + 1
            progreso_data["resultados"] = resultados
            progreso_data["fecha_modificacion"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(progreso_data, f, indent=2, ensure_ascii=False)
        
        # Finalizar el análisis
        progreso_data["estado"] = "completado"
        progreso_data["num_resultados"] = len(resultados)
        progreso_data["fecha_finalizacion"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ ANÁLISIS CON PREGUNTAS CUSTOM COMPLETADO - {len(resultados)} preguntas procesadas")
        
    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS CUSTOM: {str(e)}", exc_info=True)
        try:
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump({
                    "estado": "error",
                    "resultados": [],
                    "error": str(e),
                    "fecha_error": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")

def reanalizar_pregunta_individual_sobreescribir(contrato_path, pregunta_data, progreso_path):
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
        
        # Verificar que existe el resultado para esa pregunta
        if "resultados" not in progreso_original or len(progreso_original["resultados"]) <= num_pregunta:
            raise Exception(f"No existe resultado para la pregunta {num_pregunta}")
        
        # Leer el contrato
        with open(contrato_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Analizar la nueva pregunta
        resultado = analizar_pregunta(
            pregunta_data["pregunta"], 
            pregunta_data["seccion"], 
            pdf_bytes, 
            contrato_path.name
        )
        
        # Actualizar solo la pregunta específica en los resultados
        progreso_original["resultados"][num_pregunta].update({
            "Pregunta": pregunta_data["pregunta"],
            "Sección": pregunta_data["seccion"], 
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
            json.dump(progreso_original, f, indent=2, ensure_ascii=False)
        
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
                json.dump(progreso_actual, f, indent=2, ensure_ascii=False)
        except Exception as e2:
            logger.error(f"❌ ERROR AL GUARDAR ERROR: {str(e2)}")


def reanalizar_documento_global_sobreescribir(contrato_path, preguntas_editadas, progreso_path):
    """
    Re-analiza todas las preguntas SOBREESCRIBIENDO el análisis original.
    Mantiene el mismo ID y archivo de progreso.
    """
    logger.info(f"🔄 INICIANDO RE-ANÁLISIS GLOBAL (SOBREESCRIBIR) - {len(preguntas_editadas)} preguntas")
    
    try:
        # Leer el progreso original
        with open(progreso_path, "r", encoding="utf-8") as f:
            progreso_original = json.load(f)
        
        # Actualizar estado inicial
        progreso_original.update({
            "estado": "reanalisis_en_progreso",
            "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_reanalisis": "global",
            "progreso": 0,
            "total_preguntas": len(preguntas_editadas)
        })
        
        # Limpiar resultados anteriores pero mantener metadatos
        progreso_original["resultados"] = []
        
        # Guardar estado inicial
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_original, f, indent=2, ensure_ascii=False)
        
        # Leer el contrato
        with open(contrato_path, "rb") as f:
            pdf_bytes = f.read()
        
        nuevos_resultados = []
        
        # Procesar cada pregunta editada
        for idx, pregunta_data in enumerate(preguntas_editadas):
            logger.info(f"📝 Procesando pregunta {idx+1}/{len(preguntas_editadas)}")
            
            # Analizar la pregunta
            resultado = analizar_pregunta(
                pregunta_data["pregunta"], 
                pregunta_data["seccion"], 
                pdf_bytes, 
                contrato_path.name
            )
            
            # Añadir metadatos del re-análisis
            resultado.update({
                "Pregunta": pregunta_data["pregunta"],
                "Sección": pregunta_data["seccion"],
                "reanalizado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tipo_reanalisis": "global"
            })
            
            nuevos_resultados.append(resultado)
            
            # Actualizar progreso intermedio
            progreso_original.update({
                "progreso": idx + 1,
                "resultados": nuevos_resultados,
                "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            with open(progreso_path, "w", encoding="utf-8") as f:
                json.dump(progreso_original, f, indent=2, ensure_ascii=False)
        
        # Finalizar el análisis
        progreso_original.update({
            "estado": "completado",
            "progreso": len(preguntas_editadas),
            "num_resultados": len(nuevos_resultados),
            "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "preguntas_originales": preguntas_editadas  # Guardar las preguntas usadas
        })
        
        # Guardar resultado final
        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(progreso_original, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ RE-ANÁLISIS GLOBAL (SOBREESCRIBIR) COMPLETADO - {len(nuevos_resultados)} preguntas procesadas")
        
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
                json.dump(progreso_actual, f, indent=2, ensure_ascii=False)
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
            ("system", """You are a legal assistant specialized in contract analysis. Answer the user's question clearly and precisely, using the attached document as context.

        Your answer must be written in Markdown format, suitable for inclusion in a DOCX document (use clear sections, bullet points, or numbered lists where appropriate).

        At the end of your answer, assess the legal risk level based on the following criteria:
        - HIGH: Clauses that may create significant liabilities, unilateral termination, severe penalties, ambiguous terms favoring the other party, or lack of important protections.
        - MEDIUM: Terms that require attention but do not pose immediate risks, standard clauses that could be improved.
        - LOW: Favorable or neutral terms, standard industry clauses, or adequate protections.
        - NOT EVALUATED: If you do not have enough information to assess the risk, or the question is not applicable, finish your answer with "RISK: NOT EVALUATED".

        Finish your answer with a line that clearly states: "RISK: [HIGH/MEDIUM/LOW/NOT EVALUATED]" """),
            ("human", f"Section: {seccion}\nQuestion: {pregunta}\n\nDocument to analyze:\n{texto_contrato}")
        ])
        
        logger.info(f"📝 Enviando consulta al LLM...")
        chain = prompt | llm | StrOutputParser()
        respuesta_llm = chain.invoke({})
        logger.info(f"✅ Respuesta recibida del LLM (longitud: {len(respuesta_llm)} caracteres)")
        
        # Extraer el nivel de riesgo de la respuesta del LLM
        riesgo = "Medio"  # Valor por defecto
        
        # Buscar tanto "RISK:" (inglés) como "RIESGO:" (español) para mayor compatibilidad
        if "RISK:" in respuesta_llm.upper() or "RIESGO:" in respuesta_llm.upper():
            lineas = respuesta_llm.split('\n')
            for linea in lineas:
                linea_upper = linea.upper()
                if "RISK:" in linea_upper or "RIESGO:" in linea_upper:
                    # Mapear valores en inglés y español
                    if any(word in linea_upper for word in ["HIGH", "ALTO"]):
                        riesgo = "Alto"
                    elif any(word in linea_upper for word in ["LOW", "BAJO"]):
                        riesgo = "Bajo"
                    elif any(word in linea_upper for word in ["MEDIUM", "MEDIO"]):
                        riesgo = "Medio"
                    elif any(word in linea_upper for word in ["NOT EVALUATED", "NO EVALUADO", "SIN EVALUAR"]):
                        riesgo = "Sin evaluar"
                    break
        
        logger.info(f"🎯 Riesgo evaluado: {riesgo}")
        
        # Limpiar la respuesta removiendo la línea de riesgo para que no aparezca duplicada
        lineas_respuesta = respuesta_llm.split('\n')
        respuesta_final = '\n'.join([linea for linea in lineas_respuesta if not any(
            word in linea.upper() for word in ['RISK:', 'RIESGO:']
        )])
        
        resultado = {
            "Respuesta": respuesta_final.strip(),
            "Riesgo": riesgo
        }
        
        logger.info(f"✅ Análisis completado exitosamente")
        return resultado
        
    except Exception as e:
        logger.error(f"❌ ERROR EN ANÁLISIS CON TEXTO: {str(e)}", exc_info=True)
        return {
            "Respuesta": f"Error al procesar la pregunta: {str(e)}",
            "Riesgo": "Alto"
        }
