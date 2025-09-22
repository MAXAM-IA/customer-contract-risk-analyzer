import streamlit as st
from pathlib import Path

def aplicar_estilos_globales():
    """Aplica los estilos CSS globales a todas las páginas"""
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
        
        /* Metrics cards */
        .metric-card {
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
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
        
        /* Drag and drop mejorado */
        .drag-drop-zone {
            transition: all 0.3s ease;
        }
        .drag-drop-zone:hover {
            transform: scale(1.02);
            border-color: #16a34a !important;
            background: #f0fdf4 !important;
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
        </style>
    """, unsafe_allow_html=True)

def mostrar_header():
    """Muestra el header común con logo y título"""
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
    
    st.markdown("<div class='separator-red'></div>", unsafe_allow_html=True)
