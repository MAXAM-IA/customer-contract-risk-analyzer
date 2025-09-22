import streamlit as st
import sqlite3
import time
from pathlib import Path
from db.analisis_db import obtener_analisis_pendientes

def obtener_estadisticas_dashboard():
    """Obtiene estadísticas para el dashboard principal"""
    try:
        conn = sqlite3.connect(Path(__file__).parent.parent.parent / "analisis.db")
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

@st.fragment
def mostrar_dashboard_ejecutivo():
    # Obtener estadísticas actualizadas
    stats = obtener_estadisticas_dashboard()
    
    # Inicializar timestamp del dashboard si no existe
    if 'dashboard_last_refresh' not in st.session_state:
        st.session_state.dashboard_last_refresh = time.time()
    
    # Header del dashboard con diseño mejorado
    ultima_actualizacion = time.strftime("%H:%M:%S", time.localtime(st.session_state.dashboard_last_refresh))
    
    # Header unificado con botón integrado
    st.markdown(f"""
        <div style='
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            padding: 0.8rem 1.2rem;
            border-radius: 8px;
            margin: 0.25rem 0 1rem 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
        '>
            <div>
                <h2 style='
                    color: white;
                    margin: 0;
                    font-size: 1.1rem;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                '>
                    <span style='font-size: 1.2rem;'>📊</span>
                    Dashboard Ejecutivo
                </h2>
                <p style='
                    color: #94a3b8;
                    margin: 0.2rem 0 0 0;
                    font-size: 0.75rem;
                '>Última actualización: {ultima_actualizacion}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón de refrescar separado y bien posicionado
    col_spacer, col_button = st.columns([5, 1])
    with col_button:
        if st.button("🔄 Actualizar", help="Actualizar dashboard", key="refresh_dashboard_compact", type="primary"):
            st.session_state.dashboard_last_refresh = time.time()
            st.toast("✅ Dashboard actualizado", icon="🔄")
            st.rerun(scope="fragment")

    # Tarjetas de métricas con diseño mejorado y alineación corregida
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(220,38,38,0.25);
                border: 1px solid rgba(255,255,255,0.1);
                height: 110px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            '>
                <div style='
                    font-size: 1.5rem; 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                '>📊</div>
                <h3 style='
                    margin: 0; 
                    font-size: 1.6rem; 
                    font-weight: 700;
                    line-height: 1;
                '>{stats['total']}</h3>
                <p style='
                    margin: 0.3rem 0 0 0; 
                    font-size: 0.75rem; 
                    opacity: 0.9;
                    line-height: 1;
                '>Total Análisis</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # Calcular porcentaje de completados
        porcentaje_completados = round(100 * stats['completados'] / max(1, stats['total']), 1)
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(22,163,74,0.25);
                border: 1px solid rgba(255,255,255,0.1);
                height: 110px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            '>
                <div style='
                    font-size: 1.5rem; 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                '>✅</div>
                <h3 style='
                    margin: 0; 
                    font-size: 1.6rem; 
                    font-weight: 700;
                    line-height: 1;
                '>{stats['completados']}</h3>
                <p style='
                    margin: 0.3rem 0 0 0; 
                    font-size: 0.75rem; 
                    opacity: 0.9;
                    line-height: 1;
                '>Completados ({porcentaje_completados}%)</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(245,158,11,0.25);
                border: 1px solid rgba(255,255,255,0.1);
                height: 110px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            '>
                <div style='
                    font-size: 1.5rem; 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                '>⏳</div>
                <h3 style='
                    margin: 0; 
                    font-size: 1.6rem; 
                    font-weight: 700;
                    line-height: 1;
                '>{stats['en_progreso']}</h3>
                <p style='
                    margin: 0.3rem 0 0 0; 
                    font-size: 0.75rem; 
                    opacity: 0.9;
                    line-height: 1;
                '>En Progreso</p>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        # Caja de eficiencia (porcentaje de éxito)
        tasa_exito = round(100 * stats['completados'] / max(1, stats['total']), 0) if stats['total'] > 0 else 100
        color_tasa = "#16a34a" if tasa_exito >= 90 else "#f59e0b" if tasa_exito >= 70 else "#dc2626"
        color_tasa_dark = "#15803d" if tasa_exito >= 90 else "#d97706" if tasa_exito >= 70 else "#b91c1c"
        
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, {color_tasa} 0%, {color_tasa_dark} 100%);
                color: white;
                padding: 1rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 8px rgba(99,102,241,0.25);
                border: 1px solid rgba(255,255,255,0.1);
                height: 110px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            '>
                <div style='
                    font-size: 1.5rem; 
                    margin-bottom: 0.5rem;
                    line-height: 1;
                '>⚡</div>
                <h3 style='
                    margin: 0; 
                    font-size: 1.6rem; 
                    font-weight: 700;
                    line-height: 1;
                '>{tasa_exito:.0f}%</h3>
                <p style='
                    margin: 0.3rem 0 0 0; 
                    font-size: 0.75rem; 
                    opacity: 0.9;
                    line-height: 1;
                '>Tasa de Éxito</p>
            </div>
        """, unsafe_allow_html=True)

    # Información del último análisis compacta con mejor diseño
    if stats['ultimo_archivo'] != "Ninguno":
        # Formatear fecha si existe
        fecha_display = ""
        if stats['ultimo_fecha']:
            try:
                from datetime import datetime
                fecha_obj = datetime.fromisoformat(stats['ultimo_fecha'].replace('Z', '+00:00'))
                fecha_display = fecha_obj.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_display = stats['ultimo_fecha']
        
        st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                border: 1px solid #e2e8f0;
                border-left: 3px solid #16a34a;
                padding: 0.6rem 0.8rem;
                border-radius: 6px;
                margin: 0.7rem 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            '>
                <div style='
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                '>
                    <div style='flex: 1;'>
                        <div style='
                            display: flex;
                            align-items: center;
                            gap: 0.6rem;
                            margin-bottom: 0.3rem;
                        '>
                            <div style='
                                background: #16a34a;
                                color: white;
                                padding: 0.3rem;
                                border-radius: 4px;
                                font-size: 0.8rem;
                                display: flex;
                                align-items: center;
                            '>📄</div>
                            <h4 style='
                                margin: 0;
                                color: #0f172a;
                                font-size: 0.85rem;
                                font-weight: 600;
                            '>Último Análisis Completado</h4>
                            <div style='
                                background: #dcfce7;
                                color: #16a34a;
                                padding: 0.2rem 0.4rem;
                                border-radius: 12px;
                                font-size: 0.65rem;
                                font-weight: 600;
                                display: flex;
                                align-items: center;
                                gap: 0.2rem;
                            '>✅ OK</div>
                        </div>
                        <p style='
                            margin: 0;
                            color: #475569;
                            font-size: 0.75rem;
                            margin-left: 2.2rem;
                            line-height: 1.4;
                        '>
                            📄 {stats['ultimo_archivo'][:45]}{'...' if len(stats['ultimo_archivo']) > 45 else ''}
                            {f"<br>📅 {fecha_display}" if fecha_display else ""}
                        </p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='
                background: #fef3c7;
                border: 1px solid #f59e0b;
                border-left: 4px solid #f59e0b;
                padding: 0.8rem 1rem;
                border-radius: 8px;
                margin: 0.7rem 0;
                text-align: center;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
            '>
                <span style='font-size: 1.2rem;'>📭</span>
                <div style='
                    color: #92400e;
                    font-size: 0.85rem;
                    font-weight: 500;
                '>
                    No hay análisis registrados aún
                </div>
            </div>
        """, unsafe_allow_html=True)

def mostrar_dashboard():
    """Función principal para mostrar el dashboard"""
    # Llamar al fragment del dashboard ejecutivo
    mostrar_dashboard_ejecutivo()
    
    # Panel informativo compacto y moderno con mejor alineación
    st.markdown("""
        <div style='
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #bfdbfe;
            border-left: 4px solid #3b82f6;
            padding: 0.8rem 1rem;
            border-radius: 8px;
            margin-top: 1.2rem;
        '>
            <div style='
                display: flex;
                align-items: center;
                gap: 0.6rem;
                margin-bottom: 0.4rem;
            '>
                <div style='
                    background: #3b82f6;
                    color: white;
                    padding: 0.3rem;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    display: flex;
                    align-items: center;
                '>ℹ️</div>
                <h4 style='
                    color: #1e40af;
                    margin: 0;
                    font-size: 0.85rem;
                    font-weight: 600;
                '>Vista Ejecutiva</h4>
                <div style='
                    background: rgba(59,130,246,0.15);
                    color: #1e40af;
                    padding: 0.2rem 0.4rem;
                    border-radius: 12px;
                    font-size: 0.65rem;
                    font-weight: 600;
                '>Tiempo Real</div>
            </div>
            <p style='
                color: #1e40af;
                margin: 0;
                margin-left: 2.2rem;
                font-size: 0.75rem;
                line-height: 1.5;
            '>Métricas actualizadas automáticamente. Usa el botón 🔄 para forzar actualización.</p>
        </div>
    """, unsafe_allow_html=True)
