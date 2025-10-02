# analizador_batch.py
import pandas as pd
import json
import time
import sys
import os

def analizar_pregunta(pregunta, seccion, texto):
    time.sleep(1)
    return {
        "Respuesta": f"Respuesta a: {pregunta[:40]}...",
        "Riesgo": "Alto" if "terminate" in pregunta.lower() else "Bajo"
    }

def main(contrato_path, progreso_path, preguntas_path):
    texto_contrato = "Texto simulado del contrato..."  # o leer el texto del contrato

    preguntas_df = pd.read_excel(preguntas_path)
    results = []

    for _, row in preguntas_df.iterrows():
        numero = row["Número de Pregunta"]
        pregunta = row["Pregunta"]
        seccion = row["Sección"]

        result = {
            "Número": numero,
            "Pregunta": pregunta,
            "Sección": seccion,
            "Estado": "✅ Completed",
            "Respuesta": "",
            "Riesgo": ""
        }

        salida = analizar_pregunta(pregunta, seccion, texto_contrato)
        result["Respuesta"] = salida["Respuesta"]
        result["Riesgo"] = salida["Riesgo"]

        results.append(result)

        with open(progreso_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    contrato_path = sys.argv[1]
    progreso_path = sys.argv[2]
    preguntas_path = sys.argv[3]
    main(contrato_path, progreso_path, preguntas_path)
