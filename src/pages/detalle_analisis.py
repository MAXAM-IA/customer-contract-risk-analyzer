import streamlit as st
import pandas as pd
from pathlib import Path
import json
import requests

# --- ESTILO MAXAM ---
st.markdown("""
    <style>
    .detalle-maxam-title {
        font-size: 2em;
        font-weight: 700;
        color: #e30613;
        margin-bottom: 0.2em;
        letter-spacing: 0.5px;
    }
    .detalle-maxam-meta {
        color: #22223b;
        font-size: 1.05em;
        margin-bottom: 1.2em;
    }
    .detalle-maxam-pregunta {
        font-weight: 600;
        color: #e30613;
        font-size: 1.08em;
        margin-bottom: 0.1em;
    }
    .detalle-maxam-respuesta {
        color: #22223b;
        font-size: 1.05em;
        margin-bottom: 0.7em;
    }
    .detalle-maxam-edit {
        margin-bottom: 1.2em;
    }
    .detalle-maxam-btn {
        background: #e30613 !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 0.4em 1.1em !important;
        font-size: 1em !important;
        cursor: pointer;
        margin-right: 0.5em;
    }
    .detalle-maxam-btn:hover {
        background: #b9050f !important;
    }
    .maxam-detalle-card {
        background: #fff;
        border: 2px solid #e30613;
        border-radius: 14px;
        padding: 1.1em 1.5em 1.1em 1.5em;
        margin-bottom: 1.3em;
        box-shadow: 0 2px 12px rgba(227,6,19,0.07);
        font-family: 'Segoe UI', 'Arial', sans-serif;
        position: relative;
    }
    .maxam-detalle-title {
        font-size: 1.18em;
        font-weight: 700;
        color: #e30613;
        margin-bottom: 0.15em;
        letter-spacing: 0.5px;
    }
    .maxam-detalle-meta {
        color: #22223b;
        font-size: 0.97em;
        margin-bottom: 0.5em;
    }
    .maxam-detalle-estado {
        color: #fff;
        background: #e30613;
        display: inline-block;
        border-radius: 8px;
        padding: 0.2em 0.8em;
        font-weight: 600;
        font-size: 1em;
        margin-bottom: 0.5em;
        box-shadow: 0 1px 4px rgba(227,6,19,0.08);
    }
    .maxam-detalle-progress {
        margin-top: 0.5em;
        margin-bottom: 0.5em;
    }
    .maxam-detalle-btns {
        display: flex;
        gap: 0.7em;
        margin-top: 0.7em;
        margin-bottom: 0.7em;
    }
    </style>
""", unsafe_allow_html=True)

# --- OBTENER ID DE ANALISIS ---
analisis_id = st.session_state.get('detalle_analisis_id', None)
API_URL = "http://localhost:8000"

if not analisis_id:
    st.error("No se ha proporcionado un ID de análisis.")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def refrescar_progreso():
    progreso_path = Path(__file__).parent.parent.parent / "fastapi_backend" / "progreso" / f"{analisis_id}.json"
    with open(progreso_path, "r", encoding="utf-8") as f:
        progreso_data = f.read()
        try:
            progreso_json = json.loads(progreso_data)
        except Exception:
            st.error("El archivo de resultados está corrupto.")
            st.stop()
    return progreso_json

progreso_json = refrescar_progreso()
preguntas_originales = progreso_json.get("preguntas_originales")
resultados = progreso_json.get("resultados", [])

if preguntas_originales:
    preguntas = preguntas_originales
else:
    preguntas = resultados  # fallback legacy

# --- PROGRESO GENERAL ---
num_completadas = sum(1 for r in resultados if r.get('Estado') == '✅ Completed')
progreso_pct = int(100 * num_completadas / max(1, len(preguntas)))
st.markdown(f"<div class='maxam-detalle-card'><div class='maxam-detalle-title'>Detalle de Análisis</div><div class='maxam-detalle-meta'>ID: <code>{analisis_id[:8]}</code> &nbsp;|&nbsp; Preguntas: {len(preguntas)}</div></div>", unsafe_allow_html=True)
st.progress(progreso_pct, text=f"Progreso: {num_completadas}/{len(preguntas)} preguntas completadas")

if st.button("🔄 Refrescar progreso", use_container_width=True):
    st.rerun()

# --- FORMULARIO DE EDICIÓN Y RE-EJECUCIÓN ---
col_btns = st.columns([2, 8])
with col_btns[0]:
    reanalizar_todas = st.button("🔄 Re-analizar todas las preguntas", key="rean_todas", help="Vuelve a lanzar el análisis para todas las preguntas.", use_container_width=True)
with col_btns[1]:
    if st.session_state.get("rean_todas_progreso", False):
        st.progress(100, text="Re-analizando todas las preguntas...")

rean_progreso = st.session_state.get("rean_progreso", {})

for idx, preg in enumerate(preguntas):
    pregunta = preg.get('Pregunta', '')
    seccion = preg.get('Sección', '')
    pregunta_corta = pregunta[:60] + ('...' if len(pregunta) > 60 else '')
    with st.expander(f"Pregunta {idx+1}: {pregunta_corta}", expanded=False):
        st.markdown(f"<div class='maxam-detalle-card'><div class='maxam-detalle-title'>Pregunta {idx+1}</div>", unsafe_allow_html=True)
        nueva_pregunta = st.text_input("Editar pregunta", value=pregunta, key=f"preg_{idx}")
        st.caption(f"Sección: {seccion}")
        respuesta = ''
        if idx < len(resultados):
            respuesta = resultados[idx].get('Respuesta', '')
        # Mostrar respuesta sin HTML para evitar problemas de renderizado
        if respuesta:
            st.markdown("**Respuesta:**")
            st.write(respuesta)
        else:
            st.info("⏳ Respuesta pendiente")
        col1, col2 = st.columns([1, 5])
        with col1:
            rean_btn = st.button("🔄 Re-analizar solo esta", key=f"rean_{idx}", use_container_width=True)
        with col2:
            if rean_progreso.get(idx):
                st.progress(100, text="Re-analizando...")
        if rean_btn:
            st.session_state["rean_progreso"] = {**rean_progreso, idx: True}
            payload = {"pregunta": nueva_pregunta, "seccion": seccion}
            with st.spinner("Re-analizando pregunta..."):
                resp = requests.post(f"{API_URL}/reanalisar_pregunta/{analisis_id}/{idx}", json=payload)
            st.session_state["rean_progreso"][idx] = False
            if resp.status_code == 200:
                st.success("Pregunta re-analizada. Refrescando...")
                st.rerun()
            else:
                st.error("Error al re-analizar la pregunta.")
        st.markdown("</div>", unsafe_allow_html=True)

if reanalizar_todas:
    st.session_state["rean_todas_progreso"] = True
    with st.spinner("Re-analizando todas las preguntas..."):
        st.progress(100, text="Re-analizando todas las preguntas...")
    st.session_state["rean_todas_progreso"] = False
    st.info("(Simulado) Re-analizando todas las preguntas...")

st.info("Puedes editar las preguntas y relanzar el análisis de forma individual o global. (Funcionalidad de re-análisis individual real, global simulada)")
