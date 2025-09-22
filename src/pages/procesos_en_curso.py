import streamlit as st
from pages.modules.procesos_en_curso import mostrar_procesos
from pages.common_styles import aplicar_estilos_globales
from db.analisis_db import init_db

# Aplicar estilos globales
aplicar_estilos_globales()

# Inicializar la base de datos
init_db()

# Mostrar los procesos en curso directamente (sin header)
mostrar_procesos()
