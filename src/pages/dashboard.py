import streamlit as st
from pages.modules.dashboard import mostrar_dashboard
from pages.common_styles import aplicar_estilos_globales
from db.analisis_db import init_db

# Aplicar estilos globales
aplicar_estilos_globales()

# Inicializar la base de datos
init_db()

# Mostrar el dashboard directamente (sin header)
mostrar_dashboard()
