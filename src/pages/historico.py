import streamlit as st
from pages.modules.historico_analisis import mostrar_historico
from pages.common_styles import aplicar_estilos_globales
from db.analisis_db import init_db

# Aplicar estilos globales
aplicar_estilos_globales()

# Inicializar la base de datos
init_db()

# Mostrar el histórico de análisis directamente (sin header)
mostrar_historico()
