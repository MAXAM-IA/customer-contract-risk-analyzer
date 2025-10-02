import streamlit as st
import requests
import time
import json
import html
from pathlib import Path
from db.analisis_db import obtener_analisis_pendientes, actualizar_estado_analisis

API_URL = "http://localhost:8000"  # Cambiar en producción

# Utilidades de caché para evitar lecturas repetidas del JSON de progreso cada 3s
def _progreso_path(analisis_id: str) -> Path:
    return Path(__file__).parent.parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"

def _progreso_mtime(analisis_id: str) -> float:
    try:
        return _progreso_path(analisis_id).stat().st_mtime
    except Exception:
        return 0.0

@st.cache_data(show_spinner=False)
def _leer_progreso_cached(analisis_id: str, mtime: float):
    p = _progreso_path(analisis_id)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def verificar_backend_disponible():
    """Verifica si el backend está disponible"""
    try:
        # Timeout bajo para no bloquear la UI
        response = requests.get(f"{API_URL}/health", timeout=1)
        return response.status_code == 200
    except:
        return False

def cancelar_proceso(analisis_id):
    """Cancela un proceso de análisis"""
    try:
        # Intentar cancelar en el backend
        response = requests.delete(f"{API_URL}/proceso/{analisis_id}", timeout=2)
        
        # Eliminar archivo de progreso si existe
        progreso_path = Path(__file__).parent.parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
        if progreso_path.exists():
            progreso_path.unlink()
        
        # Actualizar estado en la base de datos - IMPORTANTE: usar el estado exacto
        from db.analisis_db import actualizar_estado_analisis
        actualizar_estado_analisis(analisis_id, "❌ Cancelado")
        
        # Debug: verificar que se actualizó correctamente
        import sqlite3
        conn = sqlite3.connect(Path(__file__).parent.parent.parent / "analisis.db")
        c = conn.cursor()
        c.execute("SELECT estado FROM analisis WHERE id=?", (analisis_id,))
        estado_actual = c.fetchone()
        conn.close()
        print(f"DEBUG: Estado después de cancelar {analisis_id}: {estado_actual}")
        
        return True, "Proceso cancelado exitosamente"
        
    except requests.exceptions.ConnectionError:
        # Si no hay conexión al backend, solo eliminar localmente
        try:
            progreso_path = Path(__file__).parent.parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
            if progreso_path.exists():
                progreso_path.unlink()
            
            from db.analisis_db import actualizar_estado_analisis
            actualizar_estado_analisis(analisis_id, "❌ Cancelado")
            
            # Debug: verificar que se actualizó correctamente
            import sqlite3
            conn = sqlite3.connect(Path(__file__).parent.parent.parent / "analisis.db")
            c = conn.cursor()
            c.execute("SELECT estado FROM analisis WHERE id=?", (analisis_id,))
            estado_actual = c.fetchone()
            conn.close()
            print(f"DEBUG: Estado después de cancelar localmente {analisis_id}: {estado_actual}")
            
            return True, "Proceso cancelado localmente (backend no disponible)"
        except Exception as e:
            return False, f"Error al cancelar proceso: {str(e)}"
    except Exception as e:
        return False, f"Error al cancelar proceso: {str(e)}"

@st.dialog("⚠️ Confirmar Cancelación")
def dialogo_cancelar_proceso(analisis_id, filename):
    """Diálogo de confirmación para cancelar un proceso"""
    
    # Verificar estado del backend
    backend_disponible = verificar_backend_disponible()
    
    # Información del proceso usando componentes nativos
    st.error("⚠️ **¿Cancelar este proceso?**")
    
    st.markdown(f"""
    **Archivo:** {filename}  
    **ID:** `{analisis_id[:8]}...`  
    **⚠️ Esta acción no se puede deshacer**
    """)
    
    # Estado del backend
    if backend_disponible:
        st.success("🟢 **Backend disponible** - Cancelación completa")
    else:
        st.warning("🟡 **Backend no disponible** - Solo limpieza local")
    
    # Información sobre qué sucederá
    st.info("""
    **🔄 ¿Qué sucederá?**
    - El proceso de análisis se detendrá inmediatamente
    - Se eliminarán los archivos de progreso
    - El análisis se marcará como "Cancelado" en el histórico
    - Los resultados parciales se perderán
    """)
    
    # Botones de confirmación
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("❌ Sí, Cancelar", type="primary", use_container_width=True,
                    help="Confirmar cancelación del proceso", key="confirmar_cancelacion"):
            with st.spinner("Cancelando proceso..."):
                exito, mensaje = cancelar_proceso(analisis_id)
                
                if exito:
                    # Limpiar el estado del diálogo ANTES del toast y rerun
                    st.session_state['mostrar_dialogo_cancelar'] = False
                    if 'cancelar_analisis_id' in st.session_state:
                        del st.session_state['cancelar_analisis_id']
                    if 'cancelar_filename' in st.session_state:
                        del st.session_state['cancelar_filename']
                    
                    # Toast de éxito
                    st.toast("✅ Proceso cancelado exitosamente", icon="✅")
                    # Rerun inmediato para actualizar la lista - usando scope completo
                    st.rerun(scope="app")
                else:
                    st.toast(f"❌ {mensaje}", icon="❌")
                    time.sleep(1)
    
    with col2:
        if st.button("🔙 No, Mantener", type="secondary", use_container_width=True,
                    help="Cancelar la operación y mantener el proceso", key="mantener_proceso"):
            # Limpiar el estado del diálogo
            st.session_state['mostrar_dialogo_cancelar'] = False
            if 'cancelar_analisis_id' in st.session_state:
                del st.session_state['cancelar_analisis_id']
            if 'cancelar_filename' in st.session_state:
                del st.session_state['cancelar_filename']
            
            # Toast en lugar de info
            st.toast("📌 Proceso mantenido", icon="📌")
            st.rerun(scope="app")

@st.fragment(run_every=3)  # Auto-actualiza cada 3 segundos
def mostrar_procesos_en_tiempo_real():
    """Fragment que se actualiza automáticamente para mostrar procesos en curso"""
    
    # Indicador de actualización automática compacto
    current_time = time.time()
    ultima_actualizacion = time.strftime("%H:%M:%S", time.localtime(current_time))
    
    st.markdown(f"""
        <div style="
            background: #ecfdf5;
            border: 1px solid #bbf7d0;
            border-radius: 4px;
            padding: 0.3rem 0.5rem;
            margin-bottom: 0.5rem;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 0.4rem;
        ">
            <span style="
                color: #065f46;
                font-size: 0.7rem;
                font-weight: 600;
            ">
                🔄 {ultima_actualizacion}
            </span>
            <span style="
                background: #10b981;
                color: white;
                padding: 0.1rem 0.3rem;
                border-radius: 6px;
                font-size: 0.65rem;
                font-weight: 600;
            ">
                3s
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    # Obtener procesos pendientes
    pendientes = obtener_analisis_pendientes()
    hay_procesos_activos = False
    
    # Debug: mostrar cuántos procesos pendientes hay (solo en desarrollo)
    # print(f"DEBUG: {len(pendientes)} procesos pendientes encontrados")
    
    if pendientes:
        for idx, row in enumerate(pendientes):
            analisis_id, filename, estado = row
            
            # Consultar el estado real desde la API
            api_estado = None
            api_detalle = None
            api_data = {}
            try:
                # Reducir timeout y evitar saturar el backend
                resp = requests.get(f"{API_URL}/estado/{analisis_id}", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    api_estado = data.get("estado")
                    api_detalle = data.get("detalle", "")
                    api_data = data
            except Exception:
                api_estado = None
            
            # Verificar si existe archivo de progreso para determinar estado más preciso
            progreso_path = _progreso_path(analisis_id)
            progreso_existe = progreso_path.exists()
            progreso_pct = 0  # Inicializar
            progreso_data = None  # Para usar más tarde
            
            # Si existe archivo de progreso, calcular porcentaje real
            if progreso_existe:
                try:
                    mtime = _progreso_mtime(analisis_id)
                    progreso_data = _leer_progreso_cached(analisis_id, mtime)
                    
                    # Validar que tenemos datos válidos
                    if not isinstance(progreso_data, dict):
                        raise ValueError("Datos de progreso inválidos")
                    
                    # Obtener el total de preguntas desde preguntas_originales
                    preguntas_originales = progreso_data.get('preguntas_originales', [])
                    total = len(preguntas_originales)
                    
                    # Obtener el progreso actual desde el campo 'progreso' que mantiene el worker
                    progreso_actual = progreso_data.get('progreso', 0)
                    
                    # Asegurar que progreso_actual es un número válido
                    if not isinstance(progreso_actual, (int, float)):
                        progreso_actual = 0
                    
                    # Calcular porcentaje basado en progreso real del worker
                    progreso_pct = int(100 * progreso_actual / max(1, total)) if total > 0 else 0
                    
                    # Si el estado en el archivo es completado, forzar 100%
                    estado_archivo = progreso_data.get('estado', '')
                    tipo_reanalisis = progreso_data.get('tipo_reanalisis', '')
                    
                    # Para reanalisis individual, verificar si está completado
                    if tipo_reanalisis.startswith('individual_pregunta_'):
                        if estado_archivo == 'completado':
                            progreso_pct = 100
                        elif estado_archivo == 'reanalisis_en_progreso':
                            progreso_pct = 50  # En progreso, mostrar 50%
                    elif estado_archivo == 'completado':
                        progreso_pct = 100
                        
                except Exception:
                    progreso_pct = 0
                    progreso_data = None
                    estado_archivo = ''
                    tipo_reanalisis = ''
            else:
                estado_archivo = ''
                tipo_reanalisis = ''
            
            # Si el proceso ya está completado según la API o si el progreso es 100%, actualizarlo en BD
            # Consideración especial para reanalisis individual: solo marcar como completado si realmente terminó
            completado = False
            if api_estado == "completado":
                completado = True
            elif progreso_pct >= 100:
                # Para reanalisis individual, solo marcar completado si el estado es 'completado'
                if tipo_reanalisis.startswith('individual_pregunta_'):
                    if estado_archivo == 'completado':
                        completado = True
                else:
                    completado = True
            
            if completado:
                actualizar_estado_analisis(analisis_id, "✅ Completed")
                continue
            
            hay_procesos_activos = True
            
            # Determinar el estado visual basado en API y archivo de progreso
            estado_archivo = progreso_data.get('estado', '') if progreso_data else ''
            tipo_reanalisis = progreso_data.get('tipo_reanalisis', '') if progreso_data else ''
            
            if api_estado == "completado" or estado_archivo == "completado" or progreso_pct >= 100:
                color_estado = "#16a34a"
                icono_estado = "✅"
                texto_estado = "Completado"
            elif estado_archivo == "reanalisis_en_progreso" and tipo_reanalisis.startswith('individual_pregunta_'):
                # Estado especial para reanalisis individual
                color_estado = "#f59e0b"
                icono_estado = "🔄"
                texto_estado = "Reprocesando"
            elif api_estado == "procesando" or (progreso_existe and api_estado in ["en_progreso", "iniciado", "running"]):
                color_estado = "#f59e0b"
                icono_estado = "📝"
                texto_estado = "Procesando documento"
            elif api_estado == "analizando" or (progreso_existe and api_estado in ["analyzing", "processing"]):
                color_estado = "#3b82f6"
                icono_estado = "🔍"
                texto_estado = "Analizando contenido"
            elif progreso_existe or api_estado in ["iniciado", "started", "en_progreso", "in_progress"]:
                # Si hay archivo de progreso o estados que indican proceso activo
                color_estado = "#8b5cf6"
                icono_estado = "🚀"
                texto_estado = "En curso"
            elif api_estado in ["pendiente", "queued", "waiting"]:
                color_estado = "#6b7280"
                icono_estado = "⏳"
                texto_estado = "En cola"
            else:
                # Estado por defecto - probablemente en curso si llegó hasta aquí
                color_estado = "#8b5cf6"
                icono_estado = "🚀"
                texto_estado = "En curso"
            
            # Card del proceso
            filename_display = filename[:40] + ('...' if len(filename) > 40 else '')
            
            with st.container():
                st.markdown(f"""
                    <div style='
                        background: #ffffff;
                        border: 1px solid #e5e7eb;
                        border-left: 2px solid {color_estado};
                        border-radius: 4px;
                        padding: 0.4rem 0.6rem;
                        margin-bottom: 0.4rem;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                    '>
                        <div style='
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 0.2rem;
                        '>
                            <div style='flex: 1;'>
                                <div style='
                                    display: flex;
                                    align-items: center;
                                    gap: 0.3rem;
                                '>
                                    <div style='
                                        background: {color_estado};
                                        color: white;
                                        padding: 0.2rem;
                                        border-radius: 3px;
                                        font-size: 0.7rem;
                                    '>{icono_estado}</div>
                                    <div>
                                        <h3 style='
                                            margin: 0;
                                            color: #1f2937;
                                            font-size: 0.8rem;
                                            font-weight: 600;
                                        '>{filename_display}</h3>
                                        <p style='
                                            margin: 0;
                                            color: #6b7280;
                                            font-size: 0.65rem;
                                        '>ID: <code>{analisis_id[:8]}...</code></p>
                                    </div>
                                </div>
                            </div>
                            <div style='
                                background: {color_estado};
                                color: white;
                                padding: 0.15rem 0.3rem;
                                border-radius: 8px;
                                font-size: 0.65rem;
                                font-weight: 600;
                                white-space: nowrap;
                            '>{texto_estado}</div>
                        </div>
                """, unsafe_allow_html=True)

                fuente_metadata = {}
                if isinstance(api_data, dict):
                    fuente_metadata.update(api_data)
                if progreso_data and isinstance(progreso_data, dict):
                    fuente_metadata.update(progreso_data)

                modelo_llm = fuente_metadata.get('modelo_llm') or fuente_metadata.get('llm_modelo') or fuente_metadata.get('llm')
                proveedor_llm = fuente_metadata.get('proveedor_llm') or fuente_metadata.get('origen_llm')

                paginas_total = fuente_metadata.get('total_paginas')
                if isinstance(paginas_total, str):
                    try:
                        paginas_total = int(paginas_total)
                    except ValueError:
                        paginas_total = None
                elif isinstance(paginas_total, (int, float)):
                    paginas_total = int(paginas_total)
                else:
                    paginas_total = None

                documentos_info = fuente_metadata.get('documentos_info')
                if isinstance(documentos_info, str):
                    try:
                        documentos_info = json.loads(documentos_info)
                    except Exception:
                        documentos_info = []
                if not isinstance(documentos_info, list):
                    documentos_info = []

                paginas_sum = sum(
                    int(doc.get('paginas', 0))
                    for doc in documentos_info
                    if isinstance(doc, dict) and isinstance(doc.get('paginas'), (int, float))
                )
                if paginas_sum and paginas_sum > 0:
                    paginas_total = paginas_sum

                if paginas_total and paginas_total > 0:
                    paginas_label = f"{paginas_total} página{'s' if paginas_total != 1 else ''}"
                elif paginas_total == 0:
                    paginas_label = "0 páginas"
                else:
                    paginas_label = "Sin datos"

                if proveedor_llm and modelo_llm:
                    llm_label = f"{proveedor_llm} · {modelo_llm}"
                elif modelo_llm:
                    llm_label = str(modelo_llm)
                elif proveedor_llm:
                    llm_label = proveedor_llm
                else:
                    llm_label = "Sin datos"

                st.markdown(
                    """
                    <div style='display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.2rem 0 0.4rem 0;'>
                        <span style='
                            display: inline-flex;
                            align-items: center;
                            gap: 0.25rem;
                            background: #eff6ff;
                            color: #1d4ed8;
                            padding: 0.2rem 0.45rem;
                            border-radius: 999px;
                            font-size: 0.65rem;
                            font-weight: 600;
                        '>🤖 {llm_label}</span>
                        <span style='
                            display: inline-flex;
                            align-items: center;
                            gap: 0.25rem;
                            background: #f1f5f9;
                            color: #0f172a;
                            padding: 0.2rem 0.45rem;
                            border-radius: 999px;
                            font-size: 0.65rem;
                            font-weight: 600;
                        '>📄 Páginas: {paginas_label}</span>
                    </div>
                    """.format(llm_label=llm_label, paginas_label=paginas_label),
                    unsafe_allow_html=True
                )

                if documentos_info:
                    badges = []
                    for doc in documentos_info:
                        if not isinstance(doc, dict):
                            continue
                        nombre_raw = doc.get('nombre', 'Documento') or 'Documento'
                        nombre_trunc = nombre_raw[:30] + ('…' if len(nombre_raw) > 30 else '')
                        nombre_html = html.escape(nombre_trunc)
                        paginas_doc = doc.get('paginas')
                        if isinstance(paginas_doc, (int, float)) and paginas_doc >= 0:
                            paginas_doc = int(paginas_doc)
                            paginas_doc_label = f"{paginas_doc} pág."
                        else:
                            paginas_doc_label = "–"
                        badges.append(
                            f"<span style=\"display:inline-flex;align-items:center;gap:0.25rem;"
                            f"background:#f8fafc;color:#0f172a;padding:0.2rem 0.45rem;border-radius:999px;"
                            f"font-size:0.62rem;font-weight:600;\">📄 {nombre_html}"
                            f"<span style=\"color:#475569;\">({paginas_doc_label})</span></span>"
                        )

                    if badges:
                        st.markdown(
                            """
                            <div style='
                                display: flex;
                                flex-direction: column;
                                gap: 0.25rem;
                                margin: -0.1rem 0 0.4rem 0;
                            '>
                                <span style='
                                    color: #0f172a;
                                    font-size: 0.65rem;
                                    font-weight: 600;
                                '>Documentos</span>
                                <div style='
                                    display: flex;
                                    flex-wrap: wrap;
                                    gap: 0.3rem;
                                '>{badges}</div>
                            </div>
                            """.format(badges="".join(badges)),
                            unsafe_allow_html=True,
                        )
                
                # Progreso con información detallada
                if progreso_existe and progreso_data:
                    try:
                        # Detectar si es un reanalisis individual
                        tipo_reanalisis = progreso_data.get('tipo_reanalisis', '')
                        estado_archivo = progreso_data.get('estado', '')
                        
                        if tipo_reanalisis.startswith('individual_pregunta_') and estado_archivo == 'reanalisis_en_progreso':
                            # Caso especial: reanalisis de una pregunta individual
                            num_pregunta = tipo_reanalisis.split('_')[-1]
                            
                            # Para reanalisis individual, el progreso es simple: 0/1 o 1/1
                            total = 1
                            num_completadas = 0  # En progreso
                            progreso_pct = 0
                            
                            # Información específica para reanalisis individual
                            st.markdown(f"""
                                <div style='
                                    background: #fefce8;
                                    border: 1px solid #facc15;
                                    border-radius: 4px;
                                    padding: 0.5rem;
                                    margin-top: 0.3rem;
                                '>
                                    <div style='
                                        display: flex;
                                        justify-content: space-between;
                                        align-items: center;
                                        margin-bottom: 0.4rem;
                                    '>
                                        <span style='
                                            color: #854d0e;
                                            font-size: 0.75rem;
                                            font-weight: 600;
                                        '>🔄 Reanalisis Pregunta #{num_pregunta}</span>
                                        <span style='
                                            color: #a16207;
                                            font-size: 0.7rem;
                                        '>⏱️ En curso...</span>
                                    </div>
                            """, unsafe_allow_html=True)
                            
                            # Barra de progreso para reanalisis individual
                            st.progress(0.5, text="Reprocesando pregunta...")
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        else:
                            # Caso normal: análisis completo o reanalisis global
                            preguntas_originales = progreso_data.get('preguntas_originales', [])
                            total = len(preguntas_originales)
                            progreso_actual = progreso_data.get('progreso', 0)
                            
                            # Número de completadas es el progreso actual
                            num_completadas = progreso_actual
                            
                            # Estimación de tiempo restante
                            if num_completadas > 0:
                                tiempo_por_pregunta = 30  # segundos estimados por pregunta
                                preguntas_restantes = total - num_completadas
                                tiempo_restante = preguntas_restantes * tiempo_por_pregunta
                                if tiempo_restante < 60:
                                    tiempo_str = f"{tiempo_restante}s"
                                else:
                                    minutos = tiempo_restante // 60
                                    tiempo_str = f"{minutos}m {tiempo_restante % 60}s"
                            else:
                                tiempo_str = "Calculando..."
                            
                            # Mostrar progreso normal
                            st.markdown(f"""
                                <div style='
                                    background: #f8f9fa;
                                    border-radius: 4px;
                                    padding: 0.5rem;
                                    margin-top: 0.3rem;
                                '>
                                    <div style='
                                        display: flex;
                                        justify-content: space-between;
                                        align-items: center;
                                        margin-bottom: 0.4rem;
                                    '>
                                        <span style='
                                            color: #374151;
                                            font-size: 0.75rem;
                                            font-weight: 600;
                                        '>{num_completadas}/{total} preguntas</span>
                                        <span style='
                                            color: #6b7280;
                                            font-size: 0.7rem;
                                        '>⏱️ {tiempo_str}</span>
                                    </div>
                            """, unsafe_allow_html=True)
                            
                            # Barra de progreso nativa de Streamlit
                            st.progress(progreso_pct / 100, text=f"{progreso_pct}% completado")
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                    except Exception:
                        st.markdown("""
                            <div style='
                                background: #fef3c7;
                                border: 1px solid #fcd34d;
                                border-radius: 4px;
                                padding: 0.4rem;
                                margin-top: 0.3rem;
                            '>
                                <span style='color: #92400e; font-size: 0.75rem;'>
                                    ⏳ Inicializando...
                                </span>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style='
                            background: #e0f2fe;
                            border: 1px solid #81d4fa;
                            border-radius: 4px;
                            padding: 0.4rem;
                            margin-top: 0.3rem;
                        '>
                            <span style='color: #0277bd; font-size: 0.75rem;'>
                                🚀 Preparando...
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Botones de acción
                col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
                
                with col_btn1:
                    if st.button("👁️ Ver Detalle", key=f"detalle_{analisis_id}", 
                               use_container_width=True, help="Ver progreso detallado"):
                        # Aquí podrías abrir un modal o navegar a detalle
                        st.info(f"Detalle del análisis {analisis_id[:8]}... (Funcionalidad por implementar)")
                
                with col_btn2:
                    if st.button("🔄 Actualizar", key=f"refresh_{analisis_id}", 
                               use_container_width=True, help="Forzar actualización de este proceso"):
                        st.toast("🔄 Proceso actualizado", icon="🔄")
                        st.rerun(scope="fragment")
                
                with col_btn3:
                    if st.button("❌", key=f"cancel_{analisis_id}", 
                               help="Cancelar proceso", 
                               use_container_width=True):
                        # Guardar datos del proceso en session_state para el diálogo
                        st.session_state['mostrar_dialogo_cancelar'] = True
                        st.session_state['cancelar_analisis_id'] = analisis_id
                        st.session_state['cancelar_filename'] = filename_display
                        st.rerun()
    
    # Estado cuando no hay procesos activos
    if not hay_procesos_activos:
        st.markdown("""
            <div style="
                background: #f8fafc;
                border: 1px dashed #cbd5e1;
                border-radius: 8px;
                padding: 1rem;
                text-align: center;
                margin: 0.5rem 0;
            ">
                <div style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.6;">🎯</div>
                <h3 style="
                    margin: 0 0 0.3rem 0;
                    color: #475569;
                    font-size: 1rem;
                    font-weight: 600;
                ">¡Todo al día!</h3>
                <p style="
                    margin: 0;
                    color: #64748b;
                    font-size: 0.8rem;
                    line-height: 1.3;
                ">No hay procesos en curso<br>
                <span style="font-size: 0.75rem; opacity: 0.8;">Visita "Nuevo Análisis" para comenzar</span></p>
            </div>
        """, unsafe_allow_html=True)

def mostrar_procesos():
    """Función principal para mostrar la sección de procesos en curso"""
    st.markdown("""
        <h2 style='
            color: #dc2626;
            text-align: center;
            margin-bottom: 0.3rem;
            font-size: 1.1rem;
            font-weight: 600;
        '>⏳ Procesos en Curso</h2>
    """, unsafe_allow_html=True)
    
    # Información introductoria muy compacta
    st.markdown("""
        <div style='
            background: #fff7ed;
            border: 1px solid #fb923c;
            border-left: 2px solid #ea580c;
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        '>
            <span style='color: #ea580c; font-size: 0.8rem;'>⏳</span>
            <span style='color: #9a3412; font-size: 0.75rem; font-weight: 600;'>Seguimiento en Tiempo Real</span>
            <span style='color: #c2410c; font-size: 0.65rem; margin-left: auto;'>⚡ Auto 3s</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Verificar si se debe mostrar el diálogo de cancelación
    if st.session_state.get('mostrar_dialogo_cancelar', False):
        analisis_id = st.session_state.get('cancelar_analisis_id', '')
        filename = st.session_state.get('cancelar_filename', '')
        
        if analisis_id and filename:
            dialogo_cancelar_proceso(analisis_id, filename)
    
    # Mostrar procesos en tiempo real usando el fragment
    mostrar_procesos_en_tiempo_real()
    
    # Separador visual discreto
    st.markdown("<div style='margin: 1rem 0; border-bottom: 1px solid #e5e7eb;'></div>", unsafe_allow_html=True)
    
    # Obtener estadísticas discretas
    try:
        import sqlite3
        conn = sqlite3.connect(Path(__file__).parent.parent.parent / "analisis.db")
        c = conn.cursor()
        
        # Análisis del día
        c.execute("""
            SELECT COUNT(*) FROM analisis 
            WHERE date(created_at) = date('now')
        """)
        hoy = c.fetchone()[0]
        
        # Análisis completados hoy
        c.execute("""
            SELECT COUNT(*) FROM analisis 
            WHERE date(created_at) = date('now') AND estado = '✅ Completed'
        """)
        completados_hoy = c.fetchone()[0]
        
        # Calcular tiempo promedio dinámico
        c.execute("""
            SELECT COUNT(*) FROM analisis 
            WHERE estado = '✅ Completed' AND date(created_at) >= date('now', '-7 days')
        """)
        completados_semana = c.fetchone()[0]
        
        # Estimación dinámica del tiempo promedio
        if completados_semana > 0:
            base_time = 5.0
            factor_optimizacion = max(0.5, 1.0 - (completados_semana * 0.05))
            tiempo_estimado = base_time * factor_optimizacion
            tiempo_promedio = f"{tiempo_estimado:.1f}min"
        else:
            tiempo_promedio = "~5min"
        
        conn.close()
        
        # Procesos activos
        active_processes = len(obtener_analisis_pendientes())
        
        # Estadísticas discretas en una sola línea
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem;'>
                    <span style='color: #6b7280; font-size: 0.75rem;'>Hoy</span><br>
                    <span style='color: #374151; font-size: 1.1rem; font-weight: 600;'>{hoy}</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem;'>
                    <span style='color: #6b7280; font-size: 0.75rem;'>Completados</span><br>
                    <span style='color: #059669; font-size: 1.1rem; font-weight: 600;'>{completados_hoy}</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem;'>
                    <span style='color: #6b7280; font-size: 0.75rem;'>Tiempo prom.</span><br>
                    <span style='color: #d97706; font-size: 1.1rem; font-weight: 600;'>{tiempo_promedio}</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Color sutil basado en carga
            if active_processes == 0:
                text_color = "#059669"
            elif active_processes <= 2:
                text_color = "#d97706"
            else:
                text_color = "#dc2626"
            
            st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem;'>
                    <span style='color: #6b7280; font-size: 0.75rem;'>En curso</span><br>
                    <span style='color: {text_color}; font-size: 1.1rem; font-weight: 600;'>{active_processes}</span>
                </div>
            """, unsafe_allow_html=True)
            
    except Exception:
        st.markdown("""
            <div style='
                text-align: center;
                padding: 0.5rem;
                color: #9ca3af;
                font-size: 0.8rem;
            '>
                Estadísticas no disponibles
            </div>
        """, unsafe_allow_html=True)
