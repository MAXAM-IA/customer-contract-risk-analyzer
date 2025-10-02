import streamlit as st
import requests
from pathlib import Path
from datetime import datetime
from db.analisis_db import guardar_analisis

API_URL = "http://localhost:8000"  # Cambiar en producción


def _generar_nombre_default(nombres_archivos):
    if not nombres_archivos:
        base = "Analisis"
    else:
        base = Path(nombres_archivos[0]).stem or "Analisis"
    return f"{base}_{datetime.now().strftime('%Y%m%d')}"

def mostrar_nuevo_analisis():
    """Render the new analysis section."""
    st.markdown("""
        <h2 style='
            color: #dc2626;
            text-align: center;
            margin-bottom: 0.3rem;
            font-size: 1.1rem;
            font-weight: 600;
        '>📄 New Contract Analysis</h2>
    """, unsafe_allow_html=True)
    
    # Compact introduction panel
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
            <span style='color: #0c4a6e; font-size: 0.75rem; font-weight: 600;'>Intelligent Analysis</span>
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
        c.execute("SELECT COUNT(*) FROM analisis WHERE estado = '✅ Completed'")
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
                <span style='font-size: 0.6rem; color: #0c4a6e; margin-left: 0.2rem;'>Completed</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Sección de carga de archivos
    # Inicializar contador de file uploader si no existe
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    uploaded_files = st.file_uploader(
        "Drag and drop your contract here or click to browse",
        type=["pdf", "docx", "txt"],
        help="Supported formats: PDF, Word (DOCX), Texto plano (TXT)",
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        accept_multiple_files=True,
    )
    
    # Procesamiento del archivo (mostrar debajo de todo cuando hay archivo seleccionado)
    if uploaded_files:
        if not isinstance(uploaded_files, list):
            files_to_process = [uploaded_files]
        else:
            files_to_process = uploaded_files

        processed_files = []

        for idx, uploaded_file in enumerate(files_to_process, start=1):
            file_bytes = uploaded_file.getvalue()
            file_size = len(file_bytes) / 1024  # KB
            mime_type = uploaded_file.type or "application/octet-stream"

            processed_files.append({
                "name": uploaded_file.name,
                "bytes": file_bytes,
                "size_kb": file_size,
                "mime": mime_type,
            })

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
                            '>Archivo #{idx}</h3>
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
                            <div style='color: #166534; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.15rem;'>SIZE</div>
                            <div style='color: #059669; font-size: 0.8rem;'>{file_size:.1f} KB</div>
                        </div>
                        <div>
                            <div style='color: #166534; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.15rem;'>TYPE</div>
                            <div style='color: #059669; font-size: 0.8rem;'>{mime_type}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        nombres_archivos = [file_info["name"] for file_info in processed_files]
        default_name = _generar_nombre_default(nombres_archivos)
        state_key = "nuevo_analisis_nombre"
        auto_key = "nuevo_analisis_nombre_auto"

        if default_name:
            if st.session_state.get(auto_key) != default_name:
                st.session_state[state_key] = default_name
                st.session_state[auto_key] = default_name

        nombre_analisis_input = st.text_input(
            "Nombre del análisis",
            key=state_key,
            help="Este nombre aparecerá en el histórico. Puedes modificarlo antes de iniciar el análisis.",
        )
        nombre_analisis = nombre_analisis_input.strip() or default_name

        if st.button(
            "🚀 Start Combined Analysis",
            key="start_analysis_combined",
            use_container_width=True,
            type="primary",
            help="Launch analysis using all selected documents",
        ):
            with st.spinner("🔄 Processing files and sending them to the analysis service..."):
                try:
                    use_pdf_attachments = bool(st.session_state.get("usar_adjuntos_pdf", False))
                    files_payload = [
                        (
                            "files",
                            (file_info["name"], file_info["bytes"], file_info["mime"]),
                        )
                        for file_info in processed_files
                    ]

                    response = requests.post(
                        f"{API_URL}/analizar",
                        files=files_payload,
                        data={
                            "use_pdf_attachments": str(use_pdf_attachments).lower(),
                            "analysis_name": nombre_analisis,
                        },
                        timeout=30,
                    )

                    if response.status_code == 200:
                        payload = response.json()
                        analisis_id = payload["id"]
                        st.session_state.analisis_id = analisis_id

                        nombre_registrado = payload.get("nombre_analisis", nombre_analisis)

                        guardar_analisis(analisis_id, nombre_registrado, "En progreso")

                        st.success(f"✅ Analysis '{nombre_registrado}' started successfully")
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
                                '>🎯 Combined Analysis in Progress</h4>
                                <p style='
                                    color: #1d4ed8;
                                    margin: 0 0 0.4rem 0;
                                    font-size: 0.75rem;
                                '>ID: <code>{analisis_id[:8]}...</code></p>
                                <p style='
                                    color: #1d4ed8;
                                    margin: 0;
                                    font-size: 0.7rem;
                                '>💡 Track it under "In Progress"</p>
                            </div>
                        """, unsafe_allow_html=True)

                        st.toast(f"✅ Análisis '{nombre_registrado}' iniciado\n🆔 ID: {analisis_id[:8]}...", icon="🚀")

                    else:
                        st.error("❌ Failed to start the analysis. Please try again.")
                        st.toast("❌ Error al procesar los archivos", icon="🚨")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Request timed out. The files might be too large.")
                    st.toast("⏱️ Timeout - files are too large", icon="⏱️")
                except Exception as e:
                    st.error(f"❌ Connection error: {str(e)}")
                    st.toast(f"❌ Error: {str(e)}", icon="🚨")

        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

        if st.button(
            "🗑️ Clear Selection",
            key="clear_all_files",
            help="Clear all selected files",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.file_uploader_key += 1
            st.session_state.pop(state_key, None)
            st.session_state.pop(auto_key, None)
            if 'analisis_id' in st.session_state:
                del st.session_state.analisis_id
            st.toast("🗑️ Files cleared", icon="🗑️")
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
                '>No file selected</h3>
                <p style='
                    margin: 0;
                    color: #868e96;
                    font-size: 0.75rem;
                '>Drag a file or use the uploader above</p>
            </div>
        """, unsafe_allow_html=True)
