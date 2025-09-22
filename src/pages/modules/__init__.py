# Módulos del sistema de análisis de contratos
from .dashboard import mostrar_dashboard
from .nuevo_analisis import mostrar_nuevo_analisis
from .procesos_en_curso import mostrar_procesos
from .historico_analisis import mostrar_historico

__all__ = [
    'mostrar_dashboard',
    'mostrar_nuevo_analisis', 
    'mostrar_procesos',
    'mostrar_historico'
]
