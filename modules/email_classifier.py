"""
Clasificador de correos usando LLM local.
Categorías: urgente, importante, informativo, spam

Optimización: clasificación en batch — todos los correos en una sola llamada al LLM.
"""
import json
import sqlite3
from modules.llm_engine import ask_llm
from modules.email_reader import DB_PATH, init_db
from modules.logger import get_logger
from config import OLLAMA_BATCH_SIZE

log = get_logger(__name__)

CATEGORIES = ["urgente", "importante", "informativo", "spam"]

BATCH_SYSTEM_PROMPT = """Eres un experto en clasificacion de correos electronicos.
Clasificaras una lista de correos. Para cada uno debes asignar UNA categoria:
- urgente: requiere respuesta o accion inmediata
- importante: relevante pero no critico de inmediato
- informativo: newsletters, notificaciones, avisos sin accion requerida
- spam: publicidad no deseada, phishing, irrelevantes

Responde UNICAMENTE con un objeto JSON valido con el formato:
{"resultados": [{"id": "id_del_correo", "categoria": "categoria"}]}
Sin explicaciones, sin texto extra, solo el JSON."""


def _parse_batch_response(response: str, expected_ids: list[str]) -> dict[str, str]:
    """Parsea la respuesta JSON del batch y retorna {id: categoria}."""
    # Extraer JSON aunque el modelo agregue texto extra
    start = response.find("{")
    end   = response.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No se encontro JSON en la respuesta del LLM")

    data = json.loads(response[start:end])
    results = {}
    for item in data.get("resultados", []):
        eid = str(item.get("id", ""))
        cat = str(item.get("categoria", "")).lower().strip()
        if eid and cat in CATEGORIES:
            results[eid] = cat

    # Fallback para IDs que no vinieron en la respuesta
    for eid in expected_ids:
        if eid not in results:
            results[eid] = "informativo"

    return results


def classify_pending(batch_size: int = None) -> dict:
    """
    Clasifica todos los correos 'sin_clasificar' usando llamadas en batch al LLM.
    Reduce las llamadas al modelo de N a ceil(N/batch_size).

    Args:
        batch_size: Correos por llamada al LLM. Por defecto usa OLLAMA_BATCH_SIZE del .env.

    Returns:
        Diccionario con conteo por categoría.
    """
    if batch_size is None:
        batch_size = OLLAMA_BATCH_SIZE

    conn = init_db()
    rows = conn.execute(
        "SELECT id, subject, body FROM emails WHERE category='sin_clasificar'"
    ).fetchall()

    if not rows:
        log.info("No hay correos pendientes de clasificar.")
        conn.close()
        return {}

    log.info("Clasificando %d correos en batches de %d...", len(rows), batch_size)
    counts = {cat: 0 for cat in CATEGORIES}

    # Dividir en batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        ids   = [r[0] for r in batch]

        # Cuerpo reducido a 200 chars para acelerar la respuesta del modelo
        items_text = ""
        for eid, subject, body in batch:
            items_text += f'\n- id: "{eid}"\n  asunto: "{subject}"\n  cuerpo: "{body[:200]}"\n'

        prompt = f"""Clasifica estos correos:\n{items_text}\nJSON de resultado:"""

        try:
            response  = ask_llm(prompt, system=BATCH_SYSTEM_PROMPT)
            cat_map   = _parse_batch_response(response, ids)

            for eid, category in cat_map.items():
                conn.execute(
                    "UPDATE emails SET category=? WHERE id=?", (category, eid)
                )
                counts[category] += 1
                log.info("[%-12s] %s", category.upper(),
                         next((r[1][:60] for r in batch if r[0] == eid), eid))

            conn.commit()

        except Exception as e:
            log.error("Error en batch %d-%d: %s — clasificando como 'informativo'",
                      i, i + batch_size, e)
            for eid in ids:
                conn.execute(
                    "UPDATE emails SET category='informativo' WHERE id=?", (eid,)
                )
                counts["informativo"] += 1
            conn.commit()

    conn.close()
    log.info("Clasificacion completada: %s", counts)
    return counts


def get_emails_by_category(category: str) -> list[dict]:
    """Retorna correos filtrados por categoría."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, subject, sender, date, body FROM emails WHERE category=?",
        (category,)
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "subject": r[1], "sender": r[2], "date": r[3], "body": r[4]}
        for r in rows
    ]
