import streamlit as st
import base64
from pathlib import Path
from dotenv import load_dotenv
 
load_dotenv()

# Páginas principales
intro_page = st.Page("./pages/intro_page.py", title="Main Page", icon="🏠")
chatbot = st.Page("./pages/chatbot.py", title="Chatbot", icon="🗓️")

# Analizador de contratos - páginas principales
inicio_analisis = st.Page("./pages/inicio_analisis.py", title="Inicio", icon="🏠")
dashboard = st.Page("./pages/dashboard.py", title="Dashboard", icon="📊")
nuevo_analisis = st.Page("./pages/nuevo_analisis.py", title="Nuevo Análisis", icon="📄")
procesos_en_curso = st.Page("./pages/procesos_en_curso.py", title="Procesos en Curso", icon="⏳")
historico = st.Page("./pages/historico.py", title="Histórico", icon="📚")

pg = st.navigation(
    {
        "Agente": [chatbot],
        "Análisis de Contratos": [inicio_analisis, dashboard, nuevo_analisis, procesos_en_curso, historico]
    }
)

st.set_page_config(
    page_title="MAXAM",
    page_icon="💊",
    layout="wide"
)

def get_base64_of_bin_file(bin_file):
    """Devuelve la cadena base64 de un archivo binario."""
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

BASE_DIR = Path(__file__).resolve().parent

logo_maxam = "maxam-logo-no-background.png"
logo_path = BASE_DIR / "images" / logo_maxam

logo_maxam_small = "maxam-logo-no-background-small.png"
logo_small_path = BASE_DIR / "images" / logo_maxam_small

st.logo(logo_path, 
        link = "https://www.maxamcorp.com/es",
        icon_image = logo_small_path, 
        size = "large")

pg.run()