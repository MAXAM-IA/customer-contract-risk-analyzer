import streamlit as st
import requests
from pathlib import Path
from db.analisis_db import guardar_analisis

API_URL = "http://localhost:8000"  # Cambiar en producción

def mostrar_nuevo_analisis():
    """Función principal para mostrar la sección de nuevo análisis"""
    st.markdown("""
        <h2 style='
            color: #dc2626;
            text-align: center;
            margin-bottom: 0.3rem;
            font-size: 1.1rem;
            font-weight: 600;
        '>📄 Nuevo Análisis de Contrato</h2>
    """, unsafe_allow_html=True)
    
    # Información introductoria muy compacta
    st.markdown("""
        <div style='
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-left: 2px solid #0ea5e9;
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        '>
            <span style='color: #0ea5e9; font-size: 0.8rem;'>📋</span>
            <span style='color: #0c4a6e; font-size: 0.75rem; font-weight: 600;'>Análisis Inteligente</span>
            <div style='margin-left: auto; display: flex; gap: 0.2rem;'>
                <span style='background: rgba(14, 165, 233, 0.1); padding: 0.1rem 0.2rem; border-radius: 2px; color: #0c4a6e; font-size: 0.6rem; font-weight: 600;'>PDF</span>
                <span style='background: rgba(14, 165, 233, 0.1); padding: 0.1rem 0.2rem; border-radius: 2px; color: #0c4a6e; font-size: 0.6rem; font-weight: 600;'>DOCX</span>
                <span style='background: rgba(14, 165, 233, 0.1); padding: 0.1rem 0.2rem; border-radius: 2px; color: #0c4a6e; font-size: 0.6rem; font-weight: 600;'>TXT</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Mostrar estadísticas compactas
    try:
        import sqlite3
        conn = sqlite3.connect(Path(__file__).parent.parent.parent / "analisis.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM analisis")
        total_analisis = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM analisis WHERE estado = '✅ Completado'")
        completados = c.fetchone()[0]
        conn.close()
    except:
        total_analisis = 0
        completados = 0
    
    st.markdown(f"""
        <div style='
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 4px;
            padding: 0.3rem 0.5rem;
            text-align: center;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: center;
            gap: 1rem;
            align-items: center;
        '>
            <div>
                <span style='font-size: 0.9rem; font-weight: 700; color: #0369a1;'>{total_analisis}</span>
                <span style='font-size: 0.6rem; color: #0c4a6e; margin-left: 0.2rem;'>Total</span>
            </div>
            <div style='border-left: 1px solid #bae6fd; height: 15px;'></div>
            <div>
                <span style='font-size: 0.9rem; font-weight: 700; color: #16a34a;'>{completados}</span>
                <span style='font-size: 0.6rem; color: #0c4a6e; margin-left: 0.2rem;'>Completados</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Sección de carga de archivos
    # Inicializar contador de file uploader si no existe
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    uploaded_file = st.file_uploader(
        "Arrastra y suelta tu contrato aquí o haz clic para seleccionar",
        type=["pdf", "docx", "txt"],
        help="Formatos soportados: PDF, Word (DOCX), Texto plano (TXT)",
        key=f"file_uploader_{st.session_state.file_uploader_key}"
    )
    
    # Procesamiento del archivo (mostrar debajo de todo cuando hay archivo seleccionado)
    if uploaded_file:
        # Información del archivo seleccionado
        file_size = len(uploaded_file.getvalue()) / 1024  # KB
        st.markdown(f"""
            <div style='
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-left: 3px solid #16a34a;
                padding: 0.8rem;
                border-radius: 6px;
                margin-bottom: 0.8rem;
            '>
                <div style='
                    display: flex;
                    align-items: center;
                    gap: 0.6rem;
                    margin-bottom: 0.6rem;
                '>
                    <div style='
                        background: #16a34a;
                        color: white;
                        padding: 0.4rem;
                        border-radius: 6px;
                        font-size: 0.9rem;
                    '>✅</div>
                    <div>
                        <h3 style='
                            margin: 0;
                            color: #166534;
                            font-size: 0.9rem;
                            font-weight: 600;
                        '>Archivo Seleccionado</h3>
                        <p style='
                            margin: 0.15rem 0 0 0;
                            color: #059669;
                            font-size: 0.75rem;
                        '>{uploaded_file.name}</p>
                    </div>
                </div>
                <div style='
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 0.6rem;
                    background: rgba(22, 163, 74, 0.05);
                    padding: 0.6rem;
                    border-radius: 4px;
                '>
                    <div>
                        <div style='color: #166534; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.15rem;'>TAMAÑO</div>
                        <div style='color: #059669; font-size: 0.8rem;'>{file_size:.1f} KB</div>
                    </div>
                    <div>
                        <div style='color: #166534; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.15rem;'>TIPO</div>
                        <div style='color: #059669; font-size: 0.8rem;'>{uploaded_file.type}</div>
                    </div>
                    <div>
                        <div style='color: #166534; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.15rem;'>ESTADO</div>
                        <div style='color: #059669; font-size: 0.8rem;'>✅ Listo</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Botones de acción para el archivo
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            if st.button("🚀 Iniciar Análisis", use_container_width=True, type="primary", 
                       help="Procesar el documento con IA para análisis de riesgos"):
                with st.spinner("🔄 Procesando archivo y enviando al sistema de análisis..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/analizar",
                            files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                            timeout=30
                        )
                        if response.status_code == 200:
                            analisis_id = response.json()["id"]
                            st.session_state.analisis_id = analisis_id
                            guardar_analisis(analisis_id, uploaded_file.name, "En progreso")
                            
                            st.success("✅ Análisis iniciado correctamente")
                            
                            # Mostrar información del análisis iniciado
                            st.markdown(f"""
                                <div style='
                                    background: #dbeafe;
                                    border: 1px solid #93c5fd;
                                    border-left: 3px solid #3b82f6;
                                    padding: 0.6rem 0.8rem;
                                    border-radius: 4px;
                                    margin-top: 0.6rem;
                                '>
                                    <h4 style='
                                        color: #1e40af;
                                        margin: 0 0 0.3rem 0;
                                        font-size: 0.85rem;
                                        font-weight: 600;
                                    '>🎯 Análisis en Progreso</h4>
                                    <p style='
                                        color: #1d4ed8;
                                        margin: 0 0 0.4rem 0;
                                        font-size: 0.75rem;
                                    '>ID: <code>{analisis_id[:8]}...</code></p>
                                    <p style='
                                        color: #1d4ed8;
                                        margin: 0;
                                        font-size: 0.7rem;
                                    '>💡 Seguimiento en "Procesos en Curso"</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.toast(f"✅ Análisis iniciado\n🆔 ID: {analisis_id[:8]}...", icon="🚀")
                            
                        else:
                            st.error("❌ Error al iniciar el análisis. Por favor, inténtalo de nuevo.")
                            st.toast("❌ Error al procesar el archivo", icon="🚨")
                    except requests.exceptions.Timeout:
                        st.error("⏱️ Tiempo de espera agotado. El archivo podría ser muy grande.")
                        st.toast("⏱️ Timeout - archivo muy grande", icon="⏱️")
                    except Exception as e:
                        st.error(f"❌ Error de conexión: {str(e)}")
                        st.toast(f"❌ Error: {str(e)}", icon="🚨")
        
        with col_btn2:
            if st.button("🗑️ Limpiar", key="clear_file", help="Limpiar archivo seleccionado", 
                       use_container_width=True, type="secondary"):
                # Incrementar el contador para forzar recreación del file_uploader
                st.session_state.file_uploader_key += 1
                # También limpiar cualquier otra variable relacionada
                if 'analisis_id' in st.session_state:
                    del st.session_state.analisis_id
                st.toast("🗑️ Archivo eliminado", icon="🗑️")
                st.rerun()
    
    else:
        # Estado cuando no hay archivo seleccionado
        st.markdown("""
            <div style='
                background: #f8f9fa;
                border: 1px dashed #dee2e6;
                border-radius: 6px;
                padding: 1rem;
                text-align: center;
                margin-bottom: 0.8rem;
            '>
                <div style='font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.5;'>📄</div>
                <h3 style='
                    margin: 0 0 0.3rem 0;
                    color: #6c757d;
                    font-size: 0.9rem;
                    font-weight: 600;
                '>Ningún archivo seleccionado</h3>
                <p style='
                    margin: 0;
                    color: #868e96;
                    font-size: 0.75rem;
                '>Arrastra un archivo o usa el selector de arriba</p>
            </div>
        """, unsafe_allow_html=True)
