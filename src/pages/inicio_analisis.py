import streamlit as st
from pages.common_styles import aplicar_estilos_globales, mostrar_header
from db.analisis_db import init_db, obtener_analisis_pendientes
import sqlite3
from pathlib import Path

# Aplicar estilos globales
aplicar_estilos_globales()

# Inicializar la base de datos
init_db()

# Mostrar header común
mostrar_header()

st.markdown("""
    <h2 style='
        color: #dc2626;
        text-align: center;
        margin-bottom: 2rem;
        font-size: 1.8rem;
        font-weight: 600;
    '>🏠 Bienvenido al Sistema de Análisis de Contratos</h2>
""", unsafe_allow_html=True)

# Información de bienvenida
st.markdown("""
    <div style='
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border: 1px solid #bae6fd;
        border-left: 4px solid #0ea5e9;
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
    '>
        <div style='
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        '>
            <div style='
                background: #0ea5e9;
                color: white;
                padding: 1rem;
                border-radius: 12px;
                font-size: 2rem;
            '>🎯</div>
            <div>
                <h3 style='
                    margin: 0 0 0.5rem 0;
                    color: #0c4a6e;
                    font-size: 1.4rem;
                    font-weight: 700;
                '>Sistema Modular de Análisis</h3>
                <p style='
                    margin: 0;
                    color: #0369a1;
                    font-size: 1.1rem;
                    line-height: 1.6;
                '>Navegue entre las diferentes secciones usando el menú lateral para acceder a todas las funcionalidades del sistema.</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Secciones disponibles
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div style='
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        ' class='card-hover'>
            <div style='
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
            '>
                <div style='
                    background: #dc2626;
                    color: white;
                    padding: 0.75rem;
                    border-radius: 10px;
                    font-size: 1.5rem;
                '>📊</div>
                <h3 style='
                    margin: 0;
                    color: #1f2937;
                    font-size: 1.2rem;
                    font-weight: 600;
                '>Dashboard</h3>
            </div>
            <p style='
                color: #6b7280;
                margin: 0;
                font-size: 0.95rem;
                line-height: 1.5;
            '>Vista ejecutiva con métricas en tiempo real, estadísticas del sistema y información del último análisis completado.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style='
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        ' class='card-hover'>
            <div style='
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
            '>
                <div style='
                    background: #f59e0b;
                    color: white;
                    padding: 0.75rem;
                    border-radius: 10px;
                    font-size: 1.5rem;
                '>⏳</div>
                <h3 style='
                    margin: 0;
                    color: #1f2937;
                    font-size: 1.2rem;
                    font-weight: 600;
                '>Procesos en Curso</h3>
            </div>
            <p style='
                color: #6b7280;
                margin: 0;
                font-size: 0.95rem;
                line-height: 1.5;
            '>Seguimiento en tiempo real de todos los análisis activos con actualización automática cada 3 segundos.</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div style='
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        ' class='card-hover'>
            <div style='
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
            '>
                <div style='
                    background: #16a34a;
                    color: white;
                    padding: 0.75rem;
                    border-radius: 10px;
                    font-size: 1.5rem;
                '>📄</div>
                <h3 style='
                    margin: 0;
                    color: #1f2937;
                    font-size: 1.2rem;
                    font-weight: 600;
                '>Nuevo Análisis</h3>
            </div>
            <p style='
                color: #6b7280;
                margin: 0;
                font-size: 0.95rem;
                line-height: 1.5;
            '>Interfaz optimizada para subir contratos (PDF, DOCX, TXT) e iniciar nuevos análisis con IA avanzada.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div style='
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        ' class='card-hover'>
            <div style='
                display: flex;
                align-items: center;
                gap: 1rem;
                margin-bottom: 1rem;
            '>
                <div style='
                    background: #6366f1;
                    color: white;
                    padding: 0.75rem;
                    border-radius: 10px;
                    font-size: 1.5rem;
                '>📚</div>
                <h3 style='
                    margin: 0;
                    color: #1f2937;
                    font-size: 1.2rem;
                    font-weight: 600;
                '>Histórico</h3>
            </div>
            <p style='
                color: #6b7280;
                margin: 0;
                font-size: 0.95rem;
                line-height: 1.5;
            '>Repositorio completo con búsqueda, filtros, paginación y opciones de exportación de todos los análisis.</p>
        </div>
    """, unsafe_allow_html=True)

# Estadísticas rápidas del sistema
try:
    conn = sqlite3.connect(Path(__file__).parent.parent / "analisis.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM analisis")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM analisis WHERE estado = '✅ Completed'")
    completados = c.fetchone()[0]
    
    pendientes = obtener_analisis_pendientes()
    en_progreso = len(pendientes)
    
    # Análisis de hoy
    c.execute("SELECT COUNT(*) FROM analisis WHERE date(created_at) = date('now')")
    hoy = c.fetchone()[0]
    
    conn.close()
    
    st.markdown("""
        <h3 style='
            color: #374151;
            text-align: center;
            margin: 2rem 0 1.5rem 0;
            font-size: 1.3rem;
            font-weight: 600;
        '>📊 Estado Actual del Sistema</h3>
    """, unsafe_allow_html=True)
    
    # Métricas en cards
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #fef2f2 0%, #fef2f2 100%);
                border: 1px solid #fecaca;
                border-left: 4px solid #dc2626;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            '>
                <div style='
                    font-size: 2rem;
                    font-weight: 700;
                    color: #dc2626;
                    margin-bottom: 0.5rem;
                '>{total}</div>
                <div style='
                    color: #991b1b;
                    font-size: 0.9rem;
                    font-weight: 600;
                '>Total Análisis</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_stat2:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #f0fdf4 0%, #f0fdf4 100%);
                border: 1px solid #bbf7d0;
                border-left: 4px solid #16a34a;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            '>
                <div style='
                    font-size: 2rem;
                    font-weight: 700;
                    color: #16a34a;
                    margin-bottom: 0.5rem;
                '>{completados}</div>
                <div style='
                    color: #166534;
                    font-size: 0.9rem;
                    font-weight: 600;
                '>Completados</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_stat3:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #fff7ed 0%, #fff7ed 100%);
                border: 1px solid #fed7aa;
                border-left: 4px solid #f59e0b;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            '>
                <div style='
                    font-size: 2rem;
                    font-weight: 700;
                    color: #f59e0b;
                    margin-bottom: 0.5rem;
                '>{en_progreso}</div>
                <div style='
                    color: #92400e;
                    font-size: 0.9rem;
                    font-weight: 600;
                '>En Progreso</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col_stat4:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #eff6ff 0%, #eff6ff 100%);
                border: 1px solid #bfdbfe;
                border-left: 4px solid #3b82f6;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            '>
                <div style='
                    font-size: 2rem;
                    font-weight: 700;
                    color: #3b82f6;
                    margin-bottom: 0.5rem;
                '>{hoy}</div>
                <div style='
                    color: #1e40af;
                    font-size: 0.9rem;
                    font-weight: 600;
                '>Hoy</div>
            </div>
        """, unsafe_allow_html=True)

except Exception:
    st.warning("⚠️ No se pudieron cargar las estadísticas del sistema")

# Call to action
st.markdown("""
    <div style='
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border: 2px solid #cbd5e1;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    '>
        <h3 style='
            margin: 0 0 1rem 0;
            color: #1e293b;
            font-size: 1.3rem;
            font-weight: 600;
        '>🚀 ¿Listo para comenzar?</h3>
        <p style='
            color: #475569;
            margin: 0 0 1.5rem 0;
            font-size: 1rem;
            line-height: 1.6;
        '>Selecciona una sección del menú lateral para comenzar a trabajar con el sistema de análisis de contratos.</p>
        <div style='
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        '>
            <div style='
                background: #dc2626;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.9rem;
            '>📊 Dashboard para métricas</div>
            <div style='
                background: #16a34a;
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.9rem;
            '>📄 Nuevo Análisis para subir contratos</div>
        </div>
    </div>
""", unsafe_allow_html=True)
