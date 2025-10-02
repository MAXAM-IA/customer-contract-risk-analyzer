import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "../analisis.db"

# Inicializa la base de datos

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analisis (
        id TEXT PRIMARY KEY,
        filename TEXT,
        estado TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# Guarda un nuevo análisis o actualiza si ya existe

def guardar_analisis(id, filename, estado):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO analisis (id, filename, estado) VALUES (?, ?, ?)", (id, filename, estado))
    conn.commit()
    conn.close()

# Actualiza el estado de un análisis

def actualizar_estado_analisis(id, estado):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE analisis SET estado=? WHERE id=?", (estado, id))
    conn.commit()
    conn.close()

# Obtiene los análisis pendientes

def obtener_analisis_pendientes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, estado FROM analisis WHERE estado != '✅ Completed' OR estado IS NULL ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows
