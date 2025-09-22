import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent.parent / "analisis.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analisis (
        id TEXT PRIMARY KEY,
        filename TEXT,
        estado TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Añadir columna resultados_json si no existe
    c.execute("PRAGMA table_info(analisis)")
    columns = [row[1] for row in c.fetchall()]
    if "resultados_json" not in columns:
        c.execute("ALTER TABLE analisis ADD COLUMN resultados_json TEXT")
    conn.commit()
    conn.close()

def guardar_analisis(id, filename, estado, resultados_json=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO analisis (id, filename, estado, resultados_json) VALUES (?, ?, ?, ?)", (id, filename, estado, resultados_json))
    conn.commit()
    conn.close()

def actualizar_estado_analisis(id, estado, resultados_json=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if resultados_json is not None:
        c.execute("UPDATE analisis SET estado=?, resultados_json=? WHERE id=?", (estado, resultados_json, id))
    else:
        c.execute("UPDATE analisis SET estado=? WHERE id=?", (estado, id))
    conn.commit()
    conn.close()

def obtener_analisis_pendientes():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, filename, estado FROM analisis WHERE (estado != '✅ Completado' AND estado != '❌ Cancelado') OR estado IS NULL ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def actualizar_resultados_analisis(id, resultados_json):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE analisis SET resultados_json=? WHERE id=?", (resultados_json, id))
    conn.commit()
    conn.close()

def obtener_resultados_analisis(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT resultados_json FROM analisis WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return None
