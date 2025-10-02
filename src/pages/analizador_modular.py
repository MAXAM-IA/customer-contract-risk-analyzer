import streamlit as st
from pathlib import Path
from pages.modules import mostrar_dashboard, mostrar_nuevo_analisis, mostrar_procesos, mostrar_historico
from db.analisis_db import init_db
import sqlite3

# Inicializar la base de datos
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
    
    /* Sidebar personalizado */
    .sidebar-nav {
        background: #f8fafc;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #e2e8f0;
    }
    
    .nav-item {
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    
    .nav-item:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
    }
    
    .nav-item.active {
        background: #dc2626;
        color: white;
        border-color: #dc2626;
    }
    
    .nav-item.active:hover {
        background: #b91c1c;
        border-color: #b91c1c;
    }
    
    /* Metrics sidebar */
    .sidebar-metric {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #dc2626;
    }
    
    /* Auto-refresh indicator */
    .auto-refresh {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
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
    </style>
""", unsafe_allow_html=True)

# Logo y header principal
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
""", unsafe_allow_html=True)

# --- SIDEBAR NAVEGACIÓN ---
with st.sidebar:
    st.markdown("""
        <div style='
            background: #f9fafb;
            border-left: 3px solid #dc2626;
            border-radius: 6px;
            padding: 0.6rem 1rem;
            margin-bottom: 1.5rem;
        '>
            <span style='
                color: #dc2626;
                font-size: 1rem;
                font-weight: 600;
                vertical-align: middle;
            '>🧭 Navegación</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Opciones de navegación
    opciones = {
        "📊 Dashboard": "dashboard",
        "📄 Nuevo Análisis": "nuevo_analisis", 
        "⏳ Procesos en Curso": "procesos_en_curso",
        "📚 Histórico": "historico_analisis"
    }
    
    # Inicializar página seleccionada
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = "dashboard"
    
    # Crear botones de navegación
    for nombre, clave in opciones.items():
        if st.button(
            nombre,
            key=f"nav_{clave}",
            use_container_width=True,
            type="primary" if st.session_state.pagina_actual == clave else "secondary"
        ):
            st.session_state.pagina_actual = clave
            st.rerun()
    
    st.markdown("---")
    
    # Estadísticas rápidas en sidebar
    try:
        conn = sqlite3.connect(Path(__file__).parent.parent / "analisis.db")
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM analisis")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM analisis WHERE estado = '✅ Completed'")
        completados = c.fetchone()[0]
        
        from db.analisis_db import obtener_analisis_pendientes
        pendientes = obtener_analisis_pendientes()
        en_progreso = len(pendientes)
        
        conn.close()
        
        st.markdown("**📈 Estadísticas**")
        st.metric("Total", total)
        st.metric("Completados", completados)
        st.metric("En Progreso", en_progreso)
        
    except Exception:
        st.markdown("**📈 Estadísticas**")
        st.info("No disponibles")
    
    st.markdown("---")
    
    # Información adicional en sidebar
    st.markdown("**ℹ️ Información**")
    st.info("Usa el menú superior para navegar entre las diferentes secciones del sistema.")
    
    # Botón de limpieza de datos
    st.markdown("**🗑️ Mantenimiento**")
    st.markdown("""
        <div style='
            background: #fffbeb;
            border: 1px solid #fed7aa;
            padding: 0.75rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        '>
            <p style='color: #92400e; margin: 0; font-size: 0.8rem;'>
                <strong>⚠️ Atención:</strong> Esta acción eliminará permanentemente todo el histórico.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Eliminar Histórico", help="Elimina todos los análisis del sistema", use_container_width=True):
        with st.spinner("Eliminando datos..."):
            try:
                conn = sqlite3.connect(Path(__file__).parent.parent / "analisis.db")
                c = conn.cursor()
                c.execute("DELETE FROM analisis")
                conn.commit()
                conn.close()
                st.success("Histórico eliminado correctamente")
                st.info("Actualiza la página para ver los cambios")
            except Exception as e:
                st.error(f"Error al eliminar histórico: {str(e)}")

# --- CONTENIDO PRINCIPAL SEGÚN LA PÁGINA SELECCIONADA ---
st.markdown("<div class='separator-red'></div>", unsafe_allow_html=True)

if st.session_state.pagina_actual == "dashboard":
    mostrar_dashboard()
elif st.session_state.pagina_actual == "nuevo_analisis":
    mostrar_nuevo_analisis()
elif st.session_state.pagina_actual == "procesos_en_curso":
    mostrar_procesos()
elif st.session_state.pagina_actual == "historico_analisis":
    mostrar_historico()

# Footer informativo
st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
st.markdown("""
    <div style='
        background: #f8fafc;
        border-top: 1px solid #e5e7eb;
        padding: 1.5rem;
        margin-top: 2rem;
        text-align: center;
        border-radius: 8px;
    '>
        <p style='
            color: #6b7280;
            margin: 0;
            font-size: 0.85rem;
        '>
            Sistema de Análisis de Contratos - MAXAM • 
            Página actual: <strong>{st.session_state.pagina_actual.replace('_', ' ').title()}</strong>
        </p>
    </div>
""", unsafe_allow_html=True)
