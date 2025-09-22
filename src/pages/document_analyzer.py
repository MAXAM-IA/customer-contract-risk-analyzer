import streamlit as st
import requests
import pandas as pd
from pathlib import Path
from db.analisis_db import init_db, guardar_analisis, actualizar_estado_analisis, obtener_analisis_pendientes
import sqlite3
import json
import time

API_URL = "http://localhost:8000"  # Cambiar en producción

# --- DIALOGO DE DETALLE DE ANALISIS MEJORADO ---
@st.dialog("Detalle de análisis", width="large")
def mostrar_detalle_dialog(analisis_id, filename):
    progreso_path = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
    
    # Cabecera del modal profesional
    st.markdown(f"""
        <div style='
            background: #f9fafb;
            border-radius: 4px 0 0 4px;
            padding: 0.75rem 1.5rem;
            margin-bottom: 1.2rem;
            margin-left: 0;
            margin-right: 0;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        '>
            <h2 style='
                font-size: 1.25rem;
                font-weight: 700;
                color: #1f2937;
                margin: 0 0 0.2rem 0;
                text-align: left;
                letter-spacing: 0.01em;
            '>{filename}</h2>
            <p style='
                margin: 0;
                color: #374151;
                font-size: 0.92rem;
                text-align: left;
            '>ID: <code>{analisis_id[:8]}...</code></p>
        </div>
    """, unsafe_allow_html=True)
    
    # Función para refrescar datos
    def refrescar_datos():
        if progreso_path.exists():
            with open(progreso_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    progreso_json = refrescar_datos()
    if progreso_json:
        preguntas = progreso_json.get('preguntas_originales') or progreso_json.get('resultados', [])
        resultados = progreso_json.get('resultados', [])
        num_completadas = sum(1 for r in resultados if r.get('Estado') == '✅ Completado')
        total = len(preguntas)
        progreso_pct = int(100 * num_completadas / max(1, total))
        
        # Panel de progreso más limpio
        st.markdown("""
        <div style='
            background: #f9fafb;
            border-left: 4px solid #dc2626;
            border-radius: 4px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
        '>
            <span style='
                color: #dc2626;
                font-size: 1rem;
                font-weight: 600;
                vertical-align: middle;
            '>📊 Progreso del análisis</span>
    """, unsafe_allow_html=True)
        
        st.progress(progreso_pct, text=f"Progreso: {num_completadas}/{total} preguntas completadas ({progreso_pct}%)")
        
        # Botones de acción centrados
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔄 Actualizar", key="refresh_modal", use_container_width=True, help="Refrescar datos del análisis"):
                progreso_json = refrescar_datos()
                st.toast("✅ Datos actualizados", icon="🔄")
                st.success("✅ Datos actualizados")
        with col2:
            if st.button("🔄 Re-analizar todas las preguntas", key="rean_todas_modal", use_container_width=True, type="primary", help="Crear un nuevo análisis con las preguntas editadas"):
                with st.spinner("🔄 Iniciando re-análisis global..."):
                    # Recolectar todas las preguntas actuales (incluyendo editadas)
                    preguntas_para_reanalisar = []
                    for idx, preg in enumerate(preguntas):
                        # Verificar si hay una versión editada en session_state
                        edit_key = f"preg_modal_{idx}"
                        
                        pregunta_actual = st.session_state.get(edit_key, preg.get('Pregunta', ''))
                        seccion_actual = preg.get('Sección', '')
                        
                        preguntas_para_reanalisar.append({
                            "numero": preg.get('Número', ''),
                            "pregunta": pregunta_actual,
                            "seccion": seccion_actual
                        })
                    
                    # Llamar al endpoint de reanálisis global
                    try:
                        response = requests.post(
                            f"{API_URL}/reanalisar_global/{analisis_id}",
                            json={"preguntas": preguntas_para_reanalisar}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            nuevo_id = data["id"]
                            # Guardar el nuevo análisis en la base de datos como "En progreso"
                            guardar_analisis(nuevo_id, f"[REANÁLISIS] {filename}", "En progreso")
                            st.toast("Re-análisis global iniciado correctamente", icon="✅")
                        else:
                            st.toast("❌ Error al iniciar el re-análisis global", icon="🚨")
                            st.error("❌ Error al iniciar el re-análisis global")
                    except Exception as e:
                        st.toast(f"❌ Error de conexión: {str(e)}", icon="🚨")
                        st.error(f"❌ Error de conexión: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Separador
        st.markdown("<div class='separator-red'></div>", unsafe_allow_html=True)
        
        # Estado de reanálisis individual
        if 'rean_progreso_modal' not in st.session_state:
            st.session_state.rean_progreso_modal = {}
        
        # Sección de preguntas mejorada
        st.markdown("""
            <h3 style='
                color: #dc2626;
                text-align: center;
                margin-bottom: 1.5em;
                font-size: 1.2em;
                font-weight: 600;
            '>📋 Preguntas del análisis</h3>
        """, unsafe_allow_html=True)
        
        for idx, preg in enumerate(preguntas):
            pregunta = preg.get('Pregunta', '')
            seccion = preg.get('Sección', '')
            respuesta = ''
            if idx < len(resultados):
                respuesta = resultados[idx].get('Respuesta', '')
            
            pregunta_corta = pregunta[:50] + ('...' if len(pregunta) > 50 else '')
            
            # Expandible más compacto para cada pregunta
            with st.expander(f"Pregunta {idx+1} - {seccion}", expanded=False):
                st.markdown(f"""
                    <div style='
                        background: #ffffff;
                        border: 1px solid #e5e7eb;
                        border-radius: 6px;
                        padding: 1rem;
                    '>
                """, unsafe_allow_html=True)
                
                # Input editable para la pregunta
                nueva_pregunta = st.text_area(
                    "Editar pregunta:", 
                    value=pregunta, 
                    key=f"preg_modal_{idx}", 
                    height=80,
                    help="Puedes modificar esta pregunta y re-analizarla individualmente"
                )
                
                # Mostrar respuesta actual
                st.markdown("**Respuesta actual:**")
                
                if respuesta:
                    st.markdown(f"""
                        <div style='
                            background: #f8f9fa;
                            padding: 1rem;
                            border-radius: 6px;
                            border-left: 3px solid #dc2626;
                            margin: 0.5rem 0 1rem 0;
                            line-height: 1.5;
                        '></div>
                    """, unsafe_allow_html=True)
                    st.write(respuesta)
                else:
                    st.info("⏳ Respuesta pendiente")
                
                # Botón de re-análisis individual
                col_btn, col_status = st.columns([2, 3])
                with col_btn:
                    rean_btn = st.button(
                        "🔄 Re-analizar pregunta", 
                        key=f"rean_modal_{idx}", 
                        use_container_width=True,
                        type="secondary",
                        help="Re-analizar solo esta pregunta con el texto modificado"
                    )
                with col_status:
                    if st.session_state.rean_progreso_modal.get(f"{analisis_id}_{idx}"):
                        st.info("🔄 Re-analizando pregunta...")
                
                if rean_btn:
                    st.session_state.rean_progreso_modal[f"{analisis_id}_{idx}"] = True
                    payload = {"pregunta": nueva_pregunta, "seccion": seccion}
                    
                    with st.spinner("🔄 Re-analizando pregunta..."):
                        try:
                            resp = requests.post(f"{API_URL}/reanalisar_pregunta/{analisis_id}/{idx}", json=payload)
                            if resp.status_code == 200:
                                st.toast("✅ Pregunta re-analizada exitosamente!", icon="🎉")
                                st.success("✅ Pregunta re-analizada exitosamente!")
                                st.session_state.rean_progreso_modal[f"{analisis_id}_{idx}"] = False
                                # Actualizar datos sin cerrar el modal
                                progreso_json = refrescar_datos()
                                st.rerun()
                            else:
                                st.toast("❌ Error al re-analizar la pregunta", icon="🚨")
                                st.error("❌ Error al re-analizar la pregunta.")
                                st.session_state.rean_progreso_modal[f"{analisis_id}_{idx}"] = False
                        except Exception as e:
                            st.toast(f"❌ Error de conexión: {str(e)}", icon="🚨")
                            st.error(f"❌ Error de conexión: {str(e)}")
                            st.session_state.rean_progreso_modal[f"{analisis_id}_{idx}"] = False
                
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style='
                text-align: center;
                padding: 3em;
                color: #dc3545;
                background: #f8d7da;
                border: 2px solid #f5c6cb;
                border-radius: 12px;
            '>
                <h3 style='margin: 0; color: #721c24;'>⚠️ Archivo no encontrado</h3>
                <p style='margin: 1em 0 0 0;'>
                    No se encontró el archivo de progreso para este análisis.
                </p>
            </div>
        """, unsafe_allow_html=True)

init_db()

# --- ESTILO GLOBAL PROFESIONAL ---
st.markdown("""
    <style>
    body, .stApp {
        background: #fafbfc !important;
        font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif;
    }
    
    /* Botones principales */
    .stButton>button {
        background: #dc2626;
        color: #ffffff;
        border-radius: 6px;
        font-weight: 500;
        border: 1px solid #dc2626;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        transition: all 0.2s ease;
        font-size: 0.875rem;
        letter-spacing: 0.025em;
    }
    .stButton>button:hover {
        background: #b91c1c;
        border-color: #b91c1c;
        box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3);
        transform: translateY(-1px);
    }
    .stButton>button:focus {
        outline: 2px solid #dc2626;
        outline-offset: 2px;
    }
    
    /* Botones con bordes rojos */
    .btn-red-outline {
        background: #ffffff !important;
        color: #dc2626 !important;
        border: 2px solid #dc2626 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .btn-red-outline:hover {
        background: #dc2626 !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(220, 38, 38, 0.3) !important;
    }
    
    /* Botones secundarios */
    .stButton>button[kind="secondary"] {
        background: #ffffff;
        color: #dc2626;
        border: 1px solid #dc2626;
    }
    .stButton>button[kind="secondary"]:hover {
        background: #fef2f2;
        border-color: #b91c1c;
        color: #b91c1c;
    }
    
    /* Botones primarios específicamente */
    .stButton>button[kind="primary"] {
        background: #dc2626 !important;
        color: #ffffff !important;
        border: 1px solid #dc2626 !important;
    }
    .stButton>button[kind="primary"]:hover {
        background: #b91c1c !important;
        border-color: #b91c1c !important;
    }
    
    /* File uploader */
    .stFileUploader>div>div {
        border: 2px dashed #d1d5db !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        padding: 2rem !important;
        transition: all 0.2s ease !important;
    }
    .stFileUploader>div>div:hover {
        border-color: #dc2626 !important;
        background: #fef2f2 !important;
    }
    
    /* Expandibles */
    .stExpander>div>div {
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    .stExpanderHeader {
        color: #111827 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    
    /* Alertas y notificaciones */
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
        border-radius: 6px !important;
        border: 1px solid transparent !important;
        font-weight: 400 !important;
    }
    .stSuccess {
        background: #f0fdf4 !important;
        color: #166534 !important;
        border-color: #bbf7d0 !important;
    }
    .stError {
        background: #fef2f2 !important;
        color: #991b1b !important;
        border-color: #fecaca !important;
    }
    .stInfo {
        background: #eff6ff !important;
        color: #1e40af !important;
        border-color: #bfdbfe !important;
    }
    .stWarning {
        background: #fffbeb !important;
        color: #92400e !important;
        border-color: #fed7aa !important;
    }
    
    /* Progress bars */
    .stProgress .st-bo {
        background-color: #dc2626 !important;
    }
    
    /* Separadores con rojo */
    .separator-red {
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #dc2626 50%, transparent 100%);
        margin: 2rem 0;
    }
    
    /* Cards hover effect */
    .card-hover {
        transition: all 0.2s ease;
    }
    .card-hover:hover {
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15);
        border-color: rgba(220, 38, 38, 0.3);
    }
    
    /* Text areas y inputs */
    .stTextArea textarea {
        border-color: #d1d5db !important;
        border-radius: 6px !important;
    }
    .stTextArea textarea:focus {
        border-color: #dc2626 !important;
        box-shadow: 0 0 0 1px #dc2626 !important;
    }
    
    /* Download buttons específicos */
    .stDownloadButton>button {
        background: #ffffff !important;
        color: #dc2626 !important;
        border: 1px solid #dc2626 !important;
    }
    .stDownloadButton>button:hover {
        background: #fef2f2 !important;
        border-color: #b91c1c !important;
    }
    
    /* Tooltips */
    .stTooltipIcon {
        color: #dc2626 !important;
    }
    
    /* Success, error, info messages */
    .stSuccess {
        border-left: 4px solid #16a34a !important;
    }
    .stError {
        border-left: 4px solid #dc2626 !important;
    }
    .stInfo {
        border-left: 4px solid #2563eb !important;
    }
    .stWarning {
        border-left: 4px solid #ea580c !important;
    }
    
    /* Códigos */
    code {
        background: #f3f4f6 !important;
        padding: 0.125rem 0.25rem !important;
        border-radius: 4px !important;
        border: 1px solid #e5e7eb !important;
        font-weight: 500 !important;
        color: #374151 !important;
        font-size: 0.875rem !important;
    }
    
    /* Cards personalizadas */
    .card-profesional {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Botones de paginación discretos */
    div[data-testid="column"] .stButton>button {
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem !important;
        min-height: 2rem !important;
        background: transparent !important;
        color: #6b7280 !important;
        border: 1px solid #d1d5db !important;
        font-weight: 400 !important;
    }
    div[data-testid="column"] .stButton>button:hover {
        background: #f3f4f6 !important;
        color: #374151 !important;
        border-color: #9ca3af !important;
        transform: none !important;
        box-shadow: none !important;
    }
    div[data-testid="column"] .stButton>button:disabled {
        background: transparent !important;
        color: #d1d5db !important;
        border-color: #e5e7eb !important;
        cursor: not-allowed !important;
    }
    
    /* Dashboard cards con animaciones */
    .metric-card {
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    /* Tabs mejorados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding-left: 1rem;
        padding-right: 1rem;
        border-radius: 6px 6px 0 0;
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        color: #6b7280;
    }
    .stTabs [aria-selected="true"] {
        background: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    
    /* Auto-refresh indicator */
    .auto-refresh {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* Vista lista compacta */
    .lista-item {
        transition: all 0.2s ease;
        border-radius: 6px;
        padding: 0.5rem;
    }
    .lista-item:hover {
        background: #f8f9fa;
        transform: translateX(4px);
        box-shadow: 0 2px 8px rgba(220,38,38,0.1);
    }
    
    /* Drag and drop mejorado */
    .drag-drop-zone {
        transition: all 0.3s ease;
    }
    .drag-drop-zone:hover {
        transform: scale(1.02);
        border-color: #16a34a !important;
        background: #f0fdf4 !important;
    }
    
    /* Progress bars animados */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #dc2626, #f59e0b, #dc2626) !important;
        background-size: 200% 100% !important;
        animation: progressGlow 2s linear infinite !important;
    }
    @keyframes progressGlow {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Notificaciones mejoradas */
    .stToast {
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
    }
    
    /* Estados de carga */
    .spinner-container {
        text-align: center;
        padding: 2rem;
    }
    
    /* Metrics sidebar */
    .sidebar-metric {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #dc2626;
    }
    
    /* Radio buttons horizontales */
    .stRadio > div {
        flex-direction: row !important;
        gap: 1rem !important;
    }
    .stRadio > div > label {
        background: #f8f9fa !important;
        padding: 0.5rem 1rem !important;
        border-radius: 6px !important;
        border: 1px solid #e9ecef !important;
        transition: all 0.2s ease !important;
    }
    .stRadio > div > label:hover {
        background: #e9ecef !important;
        border-color: #dc2626 !important;
    }
    .stRadio > div > label[data-checked="true"] {
        background: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    </style>
""", unsafe_allow_html=True)

logo_path = Path(__file__).parent.parent / "images" / "maxam-logo-no-background-small.png"
if logo_path.exists():
    st.image(str(logo_path), width=48)

st.markdown("""
            <div>
                <h1 style='
                    font-size: 1.875rem;
                    font-weight: 700;
                    color: #111827;
                    margin: 0;
                    line-height: 1.2;
                '>Analizador de Contratos</h1>
                <p style='
                    font-size: 1rem;
                    color: #6b7280;
                    margin: 0.25rem 0 0 0;
                    font-weight: 400;
                '>Sistema de análisis de riesgos contractuales</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES ---
def obtener_estadisticas_dashboard():
    """Obtiene estadísticas para el dashboard principal"""
    try:
        conn = sqlite3.connect(Path(__file__).parent.parent / "analisis.db")
        c = conn.cursor()
        
        # Total de análisis
        c.execute("SELECT COUNT(*) FROM analisis")
        total = c.fetchone()[0]
        
        # Análisis completados
        c.execute("SELECT COUNT(*) FROM analisis WHERE estado = '✅ Completado'")
        completados = c.fetchone()[0]
        
        # Análisis en progreso
        pendientes = obtener_analisis_pendientes()
        en_progreso = len(pendientes)
        
        # Último análisis
        c.execute("SELECT filename, created_at FROM analisis ORDER BY created_at DESC LIMIT 1")
        ultimo = c.fetchone()
        ultimo_archivo = ultimo[0] if ultimo else "Ninguno"
        ultimo_fecha = ultimo[1] if ultimo else ""
        
        conn.close()
        
        return {
            "total": total,
            "completados": completados,
            "en_progreso": en_progreso,
            "ultimo_archivo": ultimo_archivo,
            "ultimo_fecha": ultimo_fecha
        }
    except Exception:
        return {
            "total": 0,
            "completados": 0,
            "en_progreso": 0,
            "ultimo_archivo": "Error",
            "ultimo_fecha": ""
        }

# Función fragment para el dashboard ejecutivo con refresh manual únicamente
@st.fragment
def mostrar_dashboard_ejecutivo():
    # Obtener estadísticas actualizadas
    stats = obtener_estadisticas_dashboard()
    
    # Inicializar timestamp del dashboard si no existe
    if 'dashboard_last_refresh' not in st.session_state:
        st.session_state.dashboard_last_refresh = time.time()
    
    # Header del dashboard con diseño moderno
    st.markdown(f"""
        <div style='
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            padding: 2rem 2.5rem;
            border-radius: 16px;
            margin: 1rem 0 2rem 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            position: relative;
            overflow: hidden;
        '>
            <div style='
                position: absolute;
                top: -50%;
                right: -20%;
                width: 300px;
                height: 300px;
                background: radial-gradient(circle, rgba(220,38,38,0.15) 0%, transparent 70%);
                border-radius: 50%;
            '></div>
            <div style='
                position: relative;
                z-index: 2;
            '>
                <div style='
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 0.5rem;
                '>
                    <div>
                        <h2 style='
                            color: white;
                            margin: 0;
                            font-size: 1.8rem;
                            font-weight: 700;
                            letter-spacing: -0.025em;
                        '>📊 Dashboard Ejecutivo</h2>
                        <p style='
                            color: #94a3b8;
                            margin: 0.5rem 0 0 0;
                            font-size: 1rem;
                            font-weight: 400;
                        '>Monitoreo en tiempo real del sistema de análisis</p>
                    </div>
                    <div style='
                        background: rgba(220,38,38,0.2);
                        border: 1px solid rgba(220,38,38,0.3);
                        border-radius: 8px;
                        padding: 0.75rem 1rem;
                        color: #fca5a5;
                        font-size: 0.875rem;
                        font-weight: 500;
                    '>
                        Dashboard Ejecutivo
                        <div style='font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem;'>
                            Actualización manual
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Tarjetas de métricas renovadas con animaciones y mejor diseño - ALTURA UNIFORME
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                color: white;
                padding: 1.75rem 1.5rem;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(220,38,38,0.25);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ' class='metric-card'>
                <div style='
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 100px;
                    height: 100px;
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                    border-radius: 50%;
                '></div>
                <div style='position: relative; z-index: 2; width: 100%;'>
                    <div style='font-size: 2.5rem; margin-bottom: 0.5rem; height: 3rem; display: flex; align-items: center; justify-content: center;'>📊</div>
                    <h3 style='margin: 0; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; height: 2.5rem; display: flex; align-items: center; justify-content: center;'>{stats['total']}</h3>
                    <p style='margin: 0.75rem 0; font-size: 0.95rem; opacity: 0.9; font-weight: 500; height: 1.2rem; display: flex; align-items: center; justify-content: center;'>Total Análisis</p>
                    <div style='
                        height: 1.5rem;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-top: 0.5rem;
                    '>
                        <div style='
                            width: 80%;
                            height: 3px;
                            background: rgba(255,255,255,0.2);
                            border-radius: 2px;
                            overflow: hidden;
                        '>
                            <div style='
                                width: 100%;
                                height: 100%;
                                background: linear-gradient(90deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.3) 100%);
                                border-radius: 2px;
                                animation: pulse 2s infinite;
                            '></div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # Calcular porcentaje de completados
        porcentaje_completados = round(100 * stats['completados'] / max(1, stats['total']), 1)
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                color: white;
                padding: 1.75rem 1.5rem;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(22,163,74,0.25);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ' class='metric-card'>
                <div style='
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 100px;
                    height: 100px;
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                    border-radius: 50%;
                '></div>
                <div style='position: relative; z-index: 2; width: 100%;'>
                    <div style='font-size: 2.5rem; margin-bottom: 0.5rem; height: 3rem; display: flex; align-items: center; justify-content: center;'>✅</div>
                    <h3 style='margin: 0; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; height: 2.5rem; display: flex; align-items: center; justify-content: center;'>{stats['completados']}</h3>
                    <p style='margin: 0.75rem 0; font-size: 0.95rem; opacity: 0.9; font-weight: 500; height: 1.2rem; display: flex; align-items: center; justify-content: center;'>Completados</p>
                    <div style='
                        height: 1.5rem;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-top: 0.5rem;
                        font-size: 0.8rem;
                        opacity: 0.8;
                    '>{porcentaje_completados}% del total</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white;
                padding: 1.75rem 1.5rem;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(245,158,11,0.25);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ' class='metric-card'>
                <div style='
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 100px;
                    height: 100px;
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                    border-radius: 50%;
                '></div>
                <div style='position: relative; z-index: 2; width: 100%;'>
                    <div style='font-size: 2.5rem; margin-bottom: 0.5rem; height: 3rem; display: flex; align-items: center; justify-content: center;'>⏳</div>
                    <h3 style='margin: 0; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; height: 2.5rem; display: flex; align-items: center; justify-content: center;'>{stats['en_progreso']}</h3>
                    <p style='margin: 0.75rem 0; font-size: 0.95rem; opacity: 0.9; font-weight: 500; height: 1.2rem; display: flex; align-items: center; justify-content: center;'>En Progreso</p>
                    <div style='
                        height: 1.5rem;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-top: 0.5rem;
                        font-size: 0.8rem;
                        opacity: 0.8;
                    '>{'🔄 Procesando...' if stats['en_progreso'] > 0 else '✨ Todo al día'}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        # Botón de actualización mejorado con hora actualizada en cada refresh
        ultima_actualizacion = time.strftime("%H:%M:%S", time.localtime(st.session_state.dashboard_last_refresh))
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                color: white;
                padding: 1.75rem 1.5rem;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(99,102,241,0.25);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.1);
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ' class='metric-card'>
                <div style='
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 100px;
                    height: 100px;
                    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                    border-radius: 50%;
                '></div>
                <div style='position: relative; z-index: 2; width: 100%;'>
                    <div style='font-size: 2.5rem; margin-bottom: 0.5rem; height: 3rem; display: flex; align-items: center; justify-content: center;'>🔄</div>
                    <h3 style='margin: 0; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; height: 2.5rem; display: flex; align-items: center; justify-content: center;'>Control</h3>
                    <p style='margin: 0.75rem 0; font-size: 0.95rem; opacity: 0.9; font-weight: 500; height: 1.2rem; display: flex; align-items: center; justify-content: center;'>Sistema</p>
                    <div style='
                        height: 1.5rem;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-top: 0.5rem;
                        font-size: 0.75rem;
                        opacity: 0.8;
                    '>{ultima_actualizacion}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Botón de refresh invisible superpuesto
        st.markdown("<div style='margin-top: -200px; height: 200px; position: relative; z-index: 10;'>", unsafe_allow_html=True)
        if st.button("🔄", use_container_width=True, help="Actualizar dashboard manualmente", key="refresh_dashboard_fragment"):
            # Actualizar timestamp del dashboard
            st.session_state.dashboard_last_refresh = time.time()
            st.toast("🔄 Dashboard actualizado manualmente", icon="🔄")
            st.rerun(scope="fragment")

    # Información del último análisis con diseño mejorado
    if stats['ultimo_archivo'] != "Ninguno":
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                border: 1px solid #e2e8f0;
                border-left: 4px solid #dc2626;
                padding: 1.5rem 2rem;
                border-radius: 12px;
                margin: 2rem 0;
                box-shadow: 0 4px 16px rgba(0,0,0,0.05);
                position: relative;
                overflow: hidden;
            '>
                <div style='
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 3px;
                    background: linear-gradient(90deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%);
                '></div>
                <div style='
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                '>
                    <div style='
                        background: #dc2626;
                        color: white;
                        padding: 0.75rem;
                        border-radius: 10px;
                        font-size: 1.25rem;
                    '>📄</div>
                    <div>
                        <h4 style='
                            margin: 0 0 0.25rem 0;
                            color: #1e293b;
                            font-size: 1.1rem;
                            font-weight: 600;
                        '>Último análisis completado</h4>
                        <p style='
                            margin: 0;
                            color: #475569;
                            font-size: 0.95rem;
                        '>
                            <strong>{stats['ultimo_archivo'][:50]}{'...' if len(stats['ultimo_archivo']) > 50 else ''}</strong>
                            <span style='color: #64748b; margin-left: 0.5rem;'>• {stats['ultimo_fecha']}</span>
                        </p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# Llamar al fragment del dashboard ejecutivo
mostrar_dashboard_ejecutivo()

st.markdown("<div class='separator-red'></div>", unsafe_allow_html=True)

# --- SECCIÓN PRINCIPAL: ANÁLISIS Y PROCESOS ---
# Header de la sección principal con acciones rápidas
st.markdown("""
    <div style='
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    '>
        <div style='
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, #dc2626 0%, #f59e0b 50%, #16a34a 100%);
        '></div>
        <div style='
            display: flex;
            justify-content: space-between;
            align-items: center;
        '>
            <div>
                <h3 style='
                    margin: 0 0 0.5rem 0;
                    color: #1e293b;
                    font-size: 1.5rem;
                    font-weight: 700;
                '>📊 Centro de Análisis</h3>
                <p style='
                    margin: 0;
                    color: #64748b;
                    font-size: 1rem;
                '>Gestión centralizada de análisis de contratos</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Acciones rápidas centralizadas
st.markdown("### ⚡ Acciones Rápidas")
col_acc1, col_acc2, col_acc3, col_acc4 = st.columns(4)

with col_acc1:
    if st.button("📋 Ver Histórico", use_container_width=True, help="Ver todos los análisis completados"):
        st.session_state.expand_historico = True
        st.rerun()

with col_acc2:
    if st.button("🔍 Buscar", use_container_width=True, help="Buscar en análisis"):
        st.session_state.focus_search = True
        st.rerun()

with col_acc3:
    if st.button("📊 Estadísticas", use_container_width=True, help="Ver estadísticas detalladas"):
        st.session_state.show_stats = True
        st.rerun()

with col_acc4:
    if st.button("🔄 Actualizar", use_container_width=True, help="Refrescar toda la página"):
        st.rerun()

st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

# --- LAYOUT PRINCIPAL: DOS COLUMNAS SIMÉTRICAS ---
col_izq, col_der = st.columns([1, 1], gap="large")

# === COLUMNA IZQUIERDA: NUEVO ANÁLISIS ===
with col_izq:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white;
            padding: 0.7rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(220,38,38,0.18);
            max-width: none;
            margin-left: auto;
            margin-right: auto;
        ">
            <div style="font-size: 1.5rem; margin-bottom: 0.2rem;">📄</div>
            <h3 style="margin: 0; font-size: 1.05rem; font-weight: 600;">Nuevo Análisis</h3>
            <p style="margin: 0.2rem 0 0 0; font-size: 0.85rem; opacity: 0.9;">
                Sube un contrato para análisis
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Indicador de estado/info (simétrico al indicador de tiempo de la derecha)
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #fef2f2 0%, #fef2f2 100%);
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 0.75rem;
            margin-bottom: 1.5rem;
            text-align: center;
        ">
            <div style="
                color: #991b1b;
                font-size: 0.8rem;
                font-weight: 600;
                margin-bottom: 0.25rem;
            ">
                📄 Análisis de Contratos
            </div>
            <div style="
                background: #dc2626;
                color: white;
                padding: 0.2rem 0.5rem;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 600;
                display: inline-block;
            ">
                FORMATOS: PDF, DOCX, TXT
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Zona de drag & drop mejorada
    # Inicializar contador de file uploader si no existe
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    uploaded_file = st.file_uploader(
        "Selecciona un archivo",
        type=["pdf", "docx", "txt"],
        help="Formatos soportados: PDF, Word (DOCX), Texto plano (TXT)",
        label_visibility="collapsed",
        key=f"file_uploader_{st.session_state.file_uploader_key}"
    )
    
    if uploaded_file:
        # Información del archivo seleccionado
        st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
                border: 1px solid #bbf7d0;
                border-left: 4px solid #16a34a;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                ">
                    <div style="
                        background: #16a34a;
                        color: white;
                        padding: 0.5rem;
                        border-radius: 6px;
                        font-size: 1rem;
                    ">✅</div>
                    <div>
                        <p style="color: #166534; margin: 0; font-weight: 600; font-size: 0.95rem;">
                            Archivo seleccionado
                        </p>
                        <p style="color: #059669; margin: 0.25rem 0 0 0; font-size: 0.85rem;">
                            {uploaded_file.name}
                        </p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Botón de análisis prominente
        if st.button("🚀 Iniciar Análisis", use_container_width=True, type="primary"):
            with st.spinner("Procesando archivo..."):
                response = requests.post(
                    f"{API_URL}/analizar",
                    files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                )
                if response.status_code == 200:
                    analisis_id = response.json()["id"]
                    st.session_state.analisis_id = analisis_id
                    guardar_analisis(analisis_id, uploaded_file.name, "En progreso")
                    st.toast(f"Análisis iniciado correctamente\n🆔 ID de seguimiento: `{analisis_id[:8]}...`", icon="✅")
                    st.rerun()
                else:
                    st.toast("❌ Error al iniciar el análisis", icon="🚨")
                    st.error("❌ Error al iniciar el análisis")
        
        # Botones de control adicionales (simetría con la columna derecha)
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        
        col_clear, col_status = st.columns([1, 2])
        with col_clear:
            if st.button(
                "🗑️ Limpiar", 
                key="clear_file", 
                help="Limpiar archivo seleccionado", 
                use_container_width=True, 
                type="secondary"
            ):
                # Incrementar el contador para forzar recreación del file_uploader
                st.session_state.file_uploader_key += 1
                # También limpiar cualquier otra variable relacionada
                if 'analisis_id' in st.session_state:
                    del st.session_state.analisis_id
                st.toast("🗑️ Archivo eliminado", icon="🗑️")
                st.rerun()
        
        with col_status:
            st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                    border: 1px solid #bbf7d0;
                    border-radius: 8px;
                    padding: 0.6rem 0.8rem;
                    font-size: 0.75rem;
                    color: #166534;
                    text-align: center;
                    font-weight: 500;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                ">
                    ✅ Archivo listo para procesar
                </div>
            """, unsafe_allow_html=True)
    else:        
        # Botones de control adicionales (simetría con la columna derecha)
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #fef2f2 0%, #fef2f2 100%);
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 0.6rem 0.8rem;
                font-size: 0.75rem;
                color: #991b1b;
                text-align: center;
                font-weight: 500;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            ">
                📄 Listo para nuevo análisis
            </div>
        """, unsafe_allow_html=True)

# === COLUMNA DERECHA: PROCESOS EN CURSO ===
with col_der:
    # Función fragment para procesos en curso con auto-refresh
    @st.fragment(run_every=3)  # Auto-actualiza cada 3 segundos
    def mostrar_procesos_en_curso():
        # Header simétrico al de nuevo análisis
        st.markdown(
            """
            <div style="
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
            color: #ffffff;
            padding: 0.7rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(31,41,55,0.18);
            max-width: none;
            margin-left: auto;
            margin-right: auto;
            ">
            <div style="font-size: 1.5rem; margin-bottom: 0.2rem;">⏳</div>
            <h3 style="margin: 0; font-size: 1.05rem; font-weight: 600;">Procesos en Curso</h3>
            <p style="margin: 0.2rem 0 0 0; font-size: 0.85rem; opacity: 0.9;">
            Seguimiento en tiempo real
            </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Indicador de actualización automática simplificado y compacto
        current_time = time.time()
        ultima_actualizacion = time.strftime("%H:%M:%S", time.localtime(current_time))
        
        st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
                border: 1px solid #bbf7d0;
                border-radius: 8px;
                padding: 0.75rem;
                margin-bottom: 1.5rem;
                text-align: center;
            ">
                <div style="
                    color: #065f46;
                    font-size: 0.8rem;
                    font-weight: 600;
                    margin-bottom: 0.25rem;
                ">
                    🔄 Auto-actualización: {ultima_actualizacion}
                </div>
                <div style="
                    background: #10b981;
                    color: white;
                    padding: 0.2rem 0.5rem;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 600;
                    display: inline-block;
                ">
                    CADA 3 SEGUNDOS
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        pendientes = obtener_analisis_pendientes()
        hay_procesos_activos = False
        
        if pendientes:
            for row in pendientes:
                analisis_id, filename, estado = row
                # Consultar el estado real desde la API
                api_estado = None
                api_detalle = None
                api_porcentaje = None
                api_progreso_text = ""
                try:
                    resp = requests.get(f"{API_URL}/estado/{analisis_id}", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict) and "estado" in data:
                            api_estado = data["estado"]
                            api_detalle = data.get("detalle", "")
                            # Usar el porcentaje calculado por el backend
                            api_porcentaje = data.get("porcentaje", 0)
                            progreso_actual = data.get("progreso", 0)
                            total_preguntas = data.get("total_preguntas", 1)
                            api_progreso_text = f"{progreso_actual}/{total_preguntas} preguntas"
                except Exception as e:
                    api_estado = None
                    st.session_state.last_fragment_update = current_time
                
                # Si el proceso ya está completado, no mostrarlo pero actualizar BD
                if api_estado == "completado":
                    if estado != "✅ Completado":
                        actualizar_estado_analisis(analisis_id, "✅ Completado")
                        st.toast(f"✅ Análisis completado: {filename[:20]}...", icon="🎉")
                    continue
                
                hay_procesos_activos = True
                
                # --- CARD DE PROCESO USANDO COMPONENTES NATIVOS ---
                filename_display = filename[:35] + ('...' if len(filename) > 35 else '')
                
                # Determinar el estado visual
                if api_estado == "procesando":
                    status_emoji = "🔄"
                    status_text = "Procesando"
                    status_color = "🟡"
                elif api_estado == "analizando":
                    status_emoji = "🧠"
                    status_text = "Analizando"
                    status_color = "🔵"
                else:
                    status_emoji = "⏳"
                    status_text = "En progreso"
                    status_color = "🟠"
                
                # Crear la tarjeta usando solo componentes nativos
                with st.container():
                    # Usar st.columns para layout
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**📄 {filename_display}**")
                        st.caption(f"ID: {analisis_id[:8]}...")
                        if api_detalle:
                            st.caption(f"💭 {api_detalle}")
                    
                    with col2:
                        st.markdown(f"{status_color} **{status_emoji} {status_text}**")
                    
                    # Línea separadora
                    st.divider()
                
                # --- PROGRESO CON ANIMACIÓN EN TIEMPO REAL Y TIEMPO ESTIMADO ---
                # Usar datos del API en lugar de leer el archivo directamente
                progreso_pct = None
                progreso_text = ""
                tiempo_estimado = ""
                
                if api_porcentaje is not None:
                    progreso_pct = api_porcentaje
                    progreso_text = api_progreso_text
                else:
                    # Fallback: leer archivo local si el API no responde
                    progreso_path = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
                    if progreso_path.exists():
                        try:
                            with open(progreso_path, "r", encoding="utf-8") as f:
                                progreso_json = json.load(f)
                            if isinstance(progreso_json, dict):
                                preguntas = progreso_json.get('preguntas_originales') or progreso_json.get('resultados', [])
                                resultados = progreso_json.get('resultados', [])
                                num_completadas = sum(1 for r in resultados if r.get('Estado') == '✅ Completado')
                                total = len(preguntas)
                                progreso_pct = int(100 * num_completadas / max(1, total))
                                progreso_text = f"{num_completadas}/{total} preguntas"
                        except Exception:
                            progreso_pct = None
                
                if progreso_pct is not None:
                    # Mostrar progreso usando componentes nativos
                    st.markdown("**📊 Progreso del análisis**")
                    # El progreso_pct ya está en escala 0-100, convertir a 0-1 para st.progress
                    progress_value = progreso_pct / 100.0
                    st.progress(progress_value, text=f"{progreso_text} ({progreso_pct}% completado)")
                    
                    # Botón para ver detalles con diseño mejorado
                    if st.button(
                        "👁️ Ver Detalles en Tiempo Real", 
                        key=f"ver_detalle_live_{analisis_id}", 
                        use_container_width=True,
                        type="secondary",
                        help=f"Ver el progreso detallado del análisis {analisis_id[:8]}..."
                    ):
                        mostrar_detalle_dialog(analisis_id, filename)
                else:
                    # Estado inicial usando componentes nativos
                    st.info("🚀 Iniciando análisis... Preparando el procesamiento del documento")
                
                # Espaciado entre cards
                st.markdown("---")
        
        # Estado cuando no hay procesos activos
        if not hay_procesos_activos:
            st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                    border: 2px dashed #cbd5e1;
                    border-radius: 16px;
                    padding: 3rem 2rem;
                    text-align: center;
                    margin: 2rem 0;
                ">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
                    <h3 style="
                        margin: 0 0 0.5rem 0;
                        color: #475569;
                        font-size: 1.25rem;
                        font-weight: 600;
                    ">Todo al día</h3>
                    <p style="
                        margin: 0;
                        color: #64748b;
                        font-size: 0.9rem;
                        line-height: 1.5;
                    ">No hay procesos en curso en este momento.<br>
                    <span style="font-size: 0.8rem; opacity: 0.8;">Sube un documento para comenzar un nuevo análisis</span></p>
                </div>
            """, unsafe_allow_html=True)
        
        # Botones de control con diseño mejorado
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        
        col_refresh, col_info = st.columns([1, 2])
        with col_refresh:
            if st.button(
                "🔄 Refrescar", 
                key="refresh_procesos_manual", 
                help="Actualizar procesos manualmente", 
                use_container_width=True, 
                type="secondary"
            ):
                st.toast("🔄 Actualizando procesos...", icon="🔄")
                st.rerun(scope="fragment")
        
        with col_info:
            if hay_procesos_activos:
                st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                        border: 1px solid #93c5fd;
                        border-radius: 8px;
                        padding: 0.6rem 0.8rem;
                        font-size: 0.75rem;
                        color: #1e40af;
                        text-align: center;
                        font-weight: 500;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    ">
                        ⚡ Actualización automática cada 3 segundos
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="
                        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                        border: 1px solid #bbf7d0;
                        border-radius: 8px;
                        padding: 0.6rem 0.8rem;
                        font-size: 0.75rem;
                        color: #166534;
                        text-align: center;
                        font-weight: 500;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    ">
                        ✨ Listo para nuevos análisis
                    </div>
                """, unsafe_allow_html=True)
    
    # Llamar al fragment
    mostrar_procesos_en_curso()

st.markdown("<div class='separator-red'></div>", unsafe_allow_html=True)

# --- SIDEBAR SIMPLIFICADO ---
# Obtener estadísticas para el sidebar (fuera del fragment)
stats_sidebar = obtener_estadisticas_dashboard()

with st.sidebar:
    st.markdown("""
        <div style='
            background: #f9fafb;
            border-left: 3px solid #dc2626;
            border-radius: 6px;
            padding: 0.6rem 1rem;
            margin-bottom: 1rem;
        '>
            <span style='
                color: #dc2626;
                font-size: 1rem;
                font-weight: 600;
                vertical-align: middle;
            '>⚙️ Configuración</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Estadísticas rápidas en sidebar
    st.markdown("**📈 Estadísticas**")
    st.metric("Total", stats_sidebar['total'])
    st.metric("Completados", stats_sidebar['completados'])
    st.metric("En Progreso", stats_sidebar['en_progreso'])
    
    st.markdown("---")
    
    st.markdown("**🗑️ Limpieza de datos**")
    st.markdown("""
        <div style='
            background: #fffbeb;
            border: 1px solid #fed7aa;
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        '>
            <p style='color: #92400e; margin: 0; font-size: 0.875rem;'>
                <strong>⚠️ Atención:</strong> Esta acción eliminará permanentemente todo el histórico.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Eliminar Histórico", help="Elimina todos los análisis del sistema", use_container_width=True):
        with st.spinner("Eliminando datos..."):
            db_path = Path(__file__).parent.parent / "analisis.db"
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("DELETE FROM analisis")
            conn.commit()
            conn.close()
            # Elimina también los archivos de progreso y contratos
            progreso_dir = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso"
            contratos_dir = Path(__file__).parent.parent.parent / "fastapi_backend" / "contratos"
            for d in [progreso_dir, contratos_dir]:
                if d.exists():
                    for f in d.iterdir():
                        if f.is_file():
                            try:
                                f.unlink()
                            except Exception:
                                pass
        st.success("Histórico eliminado correctamente")
        st.info("Actualiza la página para ver los cambios")
        st.rerun()

# --- HISTÓRICO MEJORADO CON VISTA PREVIA ---
# Determinar si expandir automáticamente
expandir_historico = st.session_state.get('expand_historico', False)
if expandir_historico:
    st.session_state.expand_historico = False  # Reset flag

with st.expander("📚 Histórico de Análisis", expanded=expandir_historico):
    def obtener_analisis_completados(filtro_nombre="", fecha_desde=None, fecha_hasta=None):
        conn = sqlite3.connect(Path(__file__).parent.parent / "analisis.db")
        c = conn.cursor()
        
        query = "SELECT id, filename, created_at FROM analisis WHERE estado = '✅ Completado'"
        params = []
        
        if filtro_nombre:
            query += " AND filename LIKE ?"
            params.append(f"%{filtro_nombre}%")
        
        if fecha_desde:
            query += " AND created_at >= ?"
            params.append(str(fecha_desde))
        
        if fecha_hasta:
            query += " AND created_at <= ?"
            params.append(str(fecha_hasta) + " 23:59:59")
        
        query += " ORDER BY created_at DESC"
        
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows

    # Cabecera del histórico con botón de exportar
    col_header, col_export = st.columns([3, 1])
    
    with col_header:
        st.markdown("""
            <div style='
                background: #f9fafb;
                border-left: 4px solid #dc2626;
                border-radius: 4px;
                padding: 0.75rem 1rem;
                margin-bottom: 1rem;
            '>
                <span style='
                    color: #dc2626;
                    font-size: 1rem;
                    font-weight: 600;
                    vertical-align: middle;
                '>✅ Análisis Completados</span>
            </div>
        """, unsafe_allow_html=True)
    
    with col_export:
        st.markdown("<div style='margin-bottom: 1rem; margin-top: 0.75rem;'>", unsafe_allow_html=True)
        if st.button("📊 Exportar Todo", help="Exportar todos los análisis completados", use_container_width=True, key="export_header_button", type="secondary"):
            # Obtener todos los análisis completados (sin filtros)
            todos_completados = obtener_analisis_completados()
            if todos_completados:
                import pandas as pd
                data_export = []
                for row in todos_completados:
                    analisis_id, filename, fecha = row
                    data_export.append({
                        "ID": analisis_id,
                        "Archivo": filename,
                        "Fecha": fecha,
                        "Estado": "Completado"
                    })
                df_export = pd.DataFrame(data_export)
                csv_export = df_export.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "💾 Descargar CSV",
                    data=csv_export,
                    file_name=f"analisis_historico_completo_{len(todos_completados)}_items.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_csv_header"
                )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Filtros rápidos en tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Buscar", "📅 Por Fecha", "📊 Vista"])
    
    with tab1:
        # Focus automático en búsqueda si se solicitó
        focus_search = st.session_state.get('focus_search', False)
        if focus_search:
            st.session_state.focus_search = False
        
        filtro_nombre = st.text_input(
            "Buscar por nombre de archivo",
            key="filtro_nombre_historico",
            placeholder="Ej: contrato, acuerdo, términos...",
            help="Busca archivos que contengan este texto"
        )
    
    with tab2:
        col_fecha1, col_fecha2, col_fecha3 = st.columns([2, 2, 1])
        
        with col_fecha1:
            # Determinar el valor inicial basado en filtro rápido
            valor_inicial = ()
            if 'filtro_fecha_aplicado' in st.session_state:
                valor_inicial = st.session_state.filtro_fecha_aplicado
            
            rango_fechas = st.date_input(
                "Rango de fechas",
                key="rango_fechas_historico",
                value=valor_inicial,
                help="Selecciona un rango de fechas para filtrar"
            )
        
        with col_fecha2:
            # Filtros rápidos de fecha
            filtro_rapido = st.selectbox(
                "Filtros rápidos",
                ["Seleccionar...", "Hoy", "Esta semana", "Este mes", "Últimos 30 días"],
                key="filtro_fecha_rapido"
            )
            
            # Aplicar filtro rápido automáticamente cuando cambie la selección
            if filtro_rapido != "Seleccionar...":
                from datetime import datetime, timedelta
                hoy = datetime.now().date()
                
                if filtro_rapido == "Hoy":
                    fechas_aplicar = (hoy, hoy)
                elif filtro_rapido == "Esta semana":
                    inicio_semana = hoy - timedelta(days=hoy.weekday())
                    fechas_aplicar = (inicio_semana, hoy)
                elif filtro_rapido == "Este mes":
                    inicio_mes = hoy.replace(day=1)
                    fechas_aplicar = (inicio_mes, hoy)
                elif filtro_rapido == "Últimos 30 días":
                    hace_30_dias = hoy - timedelta(days=30)
                    fechas_aplicar = (hace_30_dias, hoy)
                
                # Aplicar automáticamente si no está ya aplicado
                if st.session_state.get('filtro_fecha_aplicado') != fechas_aplicar:
                    st.session_state.filtro_fecha_aplicada = fechas_aplicar
                    st.rerun()
            else:
                # Si se selecciona "Seleccionar...", limpiar el filtro aplicado
                if 'filtro_fecha_aplicado' in st.session_state:
                    del st.session_state.filtro_fecha_aplicado
                    st.rerun()
        
        with col_fecha3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key="limpiar_filtros", help="Limpiar filtros", use_container_width=True):
                # Limpiar todos los filtros
                if 'filtro_fecha_aplicado' in st.session_state:
                    del st.session_state.filtro_fecha_aplicado
                st.rerun()
    
    with tab3:
        col_vista1, col_vista2 = st.columns(2)
        with col_vista1:
            vista_tipo = st.radio(
                "Tipo de vista",
                ["Tarjetas", "Lista compacta"],
                key="vista_tipo_historico",
                horizontal=True
            )
        with col_vista2:
            items_por_pagina = st.selectbox(
                "Elementos por página",
                [5, 10, 15, 20],
                index=0,
                key="items_por_pagina_historico"
            )
    
    # Extraer fechas del rango (priorizar filtro aplicado si existe)
    fecha_desde = None
    fecha_hasta = None
    
    # Usar el rango de fechas aplicado si existe, sino usar el del widget
    fechas_a_usar = rango_fechas
    if 'filtro_fecha_aplicado' in st.session_state:
        fechas_a_usar = st.session_state.filtro_fecha_aplicado
    
    if isinstance(fechas_a_usar, tuple) and len(fechas_a_usar) == 2:
        fecha_desde, fecha_hasta = fechas_a_usar
    elif fechas_a_usar and not isinstance(fechas_a_usar, tuple):
        # Si solo se seleccionó una fecha, usar como fecha_desde
        fecha_desde = fechas_a_usar
    
    # Obtener análisis filtrados
    completados = obtener_analisis_completados(filtro_nombre, fecha_desde, fecha_hasta)
    
    # Usar configuración de paginación del usuario
    ITEMS_POR_PAGINA = st.session_state.get('items_por_pagina_historico', 5)
    vista_seleccionada = st.session_state.get('vista_tipo_historico', 'Tarjetas')
    
    # Configuración de paginación
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = 1
    
    total_items = len(completados)
    total_paginas = max(1, (total_items + ITEMS_POR_PAGINA - 1) // ITEMS_POR_PAGINA)
    
    # Ajustar página actual si es necesario
    if st.session_state.pagina_actual > total_paginas:
        st.session_state.pagina_actual = max(1, total_paginas)
    
    # Resumen de resultados discreto
    if total_items > 0:
        inicio = (st.session_state.pagina_actual - 1) * ITEMS_POR_PAGINA
        fin = min(inicio + ITEMS_POR_PAGINA, total_items)
        
        # Resumen discreto y limpio
        st.caption(f"📊 Mostrando {inicio + 1}-{fin} de {total_items} análisis • Página {st.session_state.pagina_actual}/{total_paginas}")
        
        # Controles de paginación en la parte superior
        if total_paginas > 1:
            st.markdown("""
                <div style='
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 6px;
                    padding: 0.5rem;
                    margin: 0.5rem 0 1rem 0;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                '>
            """, unsafe_allow_html=True)
            
            col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])
            
            with col_nav1:
                if st.button("«", disabled=(st.session_state.pagina_actual == 1), key="primera_historico_top", 
                           help="Primera página", use_container_width=True):
                    st.session_state.pagina_actual = 1
                    st.rerun()
            
            with col_nav2:
                if st.button("‹", disabled=(st.session_state.pagina_actual == 1), key="anterior_historico_top",
                           help="Página anterior", use_container_width=True):
                    st.session_state.pagina_actual -= 1
                    st.rerun()
            
            with col_nav3:
                nueva_pagina = st.selectbox(
                    "",
                    options=list(range(1, total_paginas + 1)),
                    index=st.session_state.pagina_actual - 1,
                    key="selector_pagina_historico_top",
                    format_func=lambda x: f"Página {x} de {total_paginas}",
                    label_visibility="collapsed"
                )
                if nueva_pagina != st.session_state.pagina_actual:
                    st.session_state.pagina_actual = nueva_pagina
                    st.rerun()
            
            with col_nav4:
                if st.button("›", disabled=(st.session_state.pagina_actual == total_paginas), key="siguiente_historico_top",
                           help="Página siguiente", use_container_width=True):
                    st.session_state.pagina_actual += 1
                    st.rerun()
            
            with col_nav5:
                if st.button("»", disabled=(st.session_state.pagina_actual == total_paginas), key="ultima_historico_top",
                           help="Última página", use_container_width=True):
                    st.session_state.pagina_actual = total_paginas
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Obtener elementos de la página actual
    completados_pagina = completados[inicio:fin]

    st.markdown("<hr style='margin: 0.5rem 0; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)

    if completados:
        # Renderizar según el tipo de vista seleccionado
        if vista_seleccionada == "Lista compacta":
            # Vista de lista compacta
            st.markdown("### 📋 Vista Lista")
            
            for idx, row in enumerate(completados_pagina):
                analisis_id, filename, fecha = row
                
                col_nombre, col_fecha, col_acciones = st.columns([3, 2, 2])
                
                with col_nombre:
                    st.markdown(f"""
                        <div style='padding: 0.5rem 0;'>
                            <strong style='color: #dc2626;'>{filename}</strong><br>
                            <small style='color: #6b7280;'>ID: {analisis_id[:8]}...</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_fecha:
                    st.markdown(f"""
                        <div style='padding: 0.5rem 0; text-align: center;'>
                            <span style='color: #374151;'>{fecha}</span><br>
                            <small style='color: #16a34a; font-weight: 500;'>✅ Completado</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col_acciones:
                    col_ver, col_dl = st.columns(2)
                    with col_ver:
                        if st.button("👁️", key=f"ver_lista_{analisis_id}_{inicio}", help="Ver detalles", use_container_width=True):
                            mostrar_detalle_dialog(analisis_id, filename)
                    with col_dl:
                        progreso_path = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
                        if progreso_path.exists():
                            try:
                                with open(progreso_path, "r", encoding="utf-8") as f:
                                    data = pd.read_json(f)
                                csv = data.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    "📥", 
                                    data=csv, 
                                    file_name=f"analisis_{analisis_id[:8]}.csv", 
                                    mime="text/csv", 
                                    use_container_width=True, 
                                    key=f"dl_lista_{analisis_id}_{inicio}",
                                    help="Descargar CSV"
                                )
                            except Exception:
                                st.button("❌", disabled=True, use_container_width=True, key=f"error_lista_{analisis_id}_{inicio}")
                
                # Separador entre elementos
                if idx < len(completados_pagina) - 1:
                    st.markdown("<hr style='margin: 0.5rem 0; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
        
        else:
            # Vista de tarjetas (original mejorada)
            st.markdown("### 🗂️ Vista Tarjetas")
            
            for idx, row in enumerate(completados_pagina):
                analisis_id, filename, fecha = row
                progreso_path = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
                
                # Alternar color de borde para mayor contraste
                border_color = "#dc2626" if idx % 2 == 0 else "#b91c1c"
                shadow_color = "rgba(220,38,38,0.10)" if idx % 2 == 0 else "rgba(185,28,28,0.10)"
                bg_gradient = (
                "background: linear-gradient(90deg, #fff 80%, #fef2f2 100%);"
                if idx % 2 == 0 else
                "background: linear-gradient(90deg, #fff 80%, #f3f4f6 100%);"
                )
                st.markdown(f"""
                <div style='
                    {bg_gradient}
                    border: 2.5px solid {border_color};
                    border-radius: 12px;
                    padding: 1.5rem 1.2rem 1.2rem 1.2rem;
                    margin-bottom: 2.2rem;
                    box-shadow: 0 4px 16px {shadow_color};
                    transition: box-shadow 0.2s;
                    position: relative;
                    overflow: hidden;
                ' class='card-profesional card-hover'>
                    <div style='
                    position: absolute;
                    top: 0; left: 0; width: 100%; height: 8px;
                    background: linear-gradient(90deg, {border_color} 0%, transparent 100%);
                    border-radius: 12px 12px 0 0;
                    opacity: 0.18;
                    '></div>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;'>
                    <div style='flex-grow: 1;'>
                        <h4 style='
                        color: {border_color};
                        font-weight: 700;
                        margin: 0 0 0.25rem 0;
                        font-size: 1.08rem;
                        letter-spacing: 0.01em;
                        '>{filename}</h4>
                        <div style='color: #6b7280; font-size: 0.89rem;'>
                        <span>ID: <code>{analisis_id[:8]}...</code></span>
                        <span style='margin-left: 1rem;'>Fecha: {fecha}</span>
                        </div>
                    </div>
                    <span style='
                        background: #f9fafb;
                        color: {border_color};
                        padding: 0.25rem 0.85rem;
                        border-radius: 9999px;
                        font-weight: 600;
                        font-size: 0.92rem;
                        border: 2px solid {border_color};
                        box-shadow: 0 1px 3px {shadow_color};
                        letter-spacing: 0.01em;
                    '>
                        <span style='vertical-align: middle;'>✔️ Completado</span>
                    </span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botones de acción centrados
                st.markdown("<div style='text-align: center; margin-top: 1rem;'>", unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button("👁️ Ver detalles", key=f"ver_detalle_{analisis_id}_{inicio}", use_container_width=True, help="Ver resultados del análisis"):
                        mostrar_detalle_dialog(analisis_id, filename)
                
                with col2:
                    if progreso_path.exists():
                        try:
                            with open(progreso_path, "r", encoding="utf-8") as f:
                                data = pd.read_json(f)
                            csv = data.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "📥 Descargar CSV", 
                                data=csv, 
                                file_name=f"analisis_{analisis_id[:8]}.csv", 
                                mime="text/csv", 
                                use_container_width=True, 
                                key=f"dl_{analisis_id}_{inicio}",
                                help="Descargar resultados en CSV"
                            )
                        except Exception:
                            st.button("❌ Error CSV", disabled=True, use_container_width=True, key=f"error_{analisis_id}_{inicio}")
                with col3:
                    if st.button("🔄 Re-analizar", key=f"rean_{analisis_id}_{inicio}", use_container_width=True, help="Crear nuevo análisis con las mismas preguntas", type="secondary"):
                        st.info("💡 Para re-analizar, haz clic en 'Ver detalles' y luego en 'Re-analizar todas las preguntas'")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Separador visual entre tarjetas
                if idx < len(completados_pagina) - 1:
                    st.markdown("""
                    <div style='
                        width: 100%;
                        height: 0;
                        border-bottom: 3px dashed #e5e7eb;
                        margin: 2.5rem 0 2.5rem 0;
                        opacity: 0.7;
                    '></div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Controles de paginación al final (duplicados)
        if total_paginas > 1:
            st.markdown("<hr style='margin: 0.5rem 0 2rem 0; border: 1px solid #e5e7eb;'>", unsafe_allow_html=True)
            
            col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])
            
            with col_nav1:
                if st.button("«", disabled=(st.session_state.pagina_actual == 1), key="primera_historico_bottom", 
                           help="Primera página", use_container_width=True):
                    st.session_state.pagina_actual = 1
                    st.rerun()
            
            with col_nav2:
                if st.button("‹", disabled=(st.session_state.pagina_actual == 1), key="anterior_historico_bottom",
                           help="Página anterior", use_container_width=True):
                    st.session_state.pagina_actual -= 1
                    st.rerun()
            
            with col_nav3:
                # Selector de página discreto
                nueva_pagina = st.selectbox(
                    "",
                    options=list(range(1, total_paginas + 1)),
                    index=st.session_state.pagina_actual - 1,
                    key="selector_pagina_historico_bottom",
                    format_func=lambda x: f"Página {x} de {total_paginas}",
                    label_visibility="collapsed"
                )
                if nueva_pagina != st.session_state.pagina_actual:
                    st.session_state.pagina_actual = nueva_pagina
                    st.rerun()
            
            with col_nav4:
                if st.button("›", disabled=(st.session_state.pagina_actual == total_paginas), key="siguiente_historico_bottom",
                           help="Página siguiente", use_container_width=True):
                    st.session_state.pagina_actual += 1
                    st.rerun()
            
            with col_nav5:
                if st.button("»", disabled=(st.session_state.pagina_actual == total_paginas), key="ultima_historico_bottom",
                           help="Última página", use_container_width=True):
                    st.session_state.pagina_actual = total_paginas
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        # Estados vacíos mejorados
        if filtro_nombre or rango_fechas:
            st.markdown("""
                <div style='
                    text-align: center;
                    padding: 3rem;
                    color: #6b7280;
                    background: #f9fafb;
                    border: 2px dashed #d1d5db;
                    border-radius: 12px;
                '>
                    <h3 style='margin: 0; color: #374151;'>🔍 Sin resultados</h3>
                    <p style='margin: 1rem 0 0 0; font-size: 0.875rem;'>
                        No se encontraron análisis con esos filtros
                    </p>
                    <p style='margin: 0.5rem 0 0 0; font-size: 0.75rem; color: #9ca3af;'>
                        Prueba con términos de búsqueda diferentes o limpia los filtros
                    </p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style='
                    text-align: center;
                    padding: 3rem;
                    color: #6b7280;
                    background: #f9fafb;
                    border: 2px dashed #d1d5db;
                    border-radius: 12px;
                '>
                    <h3 style='margin: 0; color: #374151;'>📂 Historial vacío</h3>
                    <p style='margin: 1rem 0 0 0; font-size: 0.875rem;'>No hay análisis completados</p>
                    <p style='margin: 0.5rem 0 0 0; font-size: 0.75rem; color: #9ca3af;'>
                        Los análisis finalizados aparecerán aquí
                    </p>
                </div>
            """, unsafe_allow_html=True)

