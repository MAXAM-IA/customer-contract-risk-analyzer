import streamlit as st
from pages.modules.nuevo_analisis import mostrar_nuevo_analisis
from pages.common_styles import aplicar_estilos_globales
from db.analisis_db import init_db

# Aplicar estilos globales
aplicar_estilos_globales()

# Inicializar la base de datos
init_db()

# Mostrar la funcionalidad de nuevo análisis directamente (sin header)
mostrar_nuevo_analisis()
