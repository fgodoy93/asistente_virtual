"""
Clasificador de correos usando LLM local.
Categorías: urgente, importante, informativo, spam
"""
import sqlite3
from modules.llm_engine import ask_llm
from modules.email_reader import DB_PATH, init_db

CATEGORIES = ["urgente", "importante", "informativo", "spam"]

SYSTEM_PROMPT = """Eres un asistente experto en clasificacion de correos electronicos.
Tu unica tarea es clasificar el correo que se te presenta en UNA de estas categorias:
- urgente: requiere respuesta o accion inmediata
- importante: relevante pero no critico de inmediato
- informativo: newsletters, notificaciones, avisos sin accion requerida
- spam: publicidad no deseada, phishing, correos irrelevantes

Responde UNICAMENTE con una de las cuatro palabras exactas. Sin explicacion, sin puntuacion."""


def classify_email(subject: str, body: str) -> str:
    """Clasifica un correo con el LLM y retorna la categoría."""
    prompt = f"""Asunto: {subject}
Cuerpo (primeras 800 palabras): {body[:800]}

Categoria:"""
    result = ask_llm(prompt, system=SYSTEM_PROMPT).lower().strip().rstrip(".")
    # Validar que la respuesta sea una categoría válida
    for cat in CATEGORIES:
        if cat in result:
            return cat
    return "informativo"


def classify_pending() -> dict:
    """
    Clasifica todos los correos con categoría 'sin_clasificar' en la BD.

    Returns:
        Diccionario con conteo por categoría.
    """
    conn = init_db()
    rows = conn.execute(
        "SELECT id, subject, body FROM emails WHERE category='sin_clasificar'"
    ).fetchall()

    if not rows:
        print("  No hay correos pendientes de clasificar.")
        conn.close()
        return {}

    print(f"  Clasificando {len(rows)} correos...")
    counts = {cat: 0 for cat in CATEGORIES}

    for eid, subject, body in rows:
        try:
            category = classify_email(subject, body)
            conn.execute(
                "UPDATE emails SET category=? WHERE id=?", (category, eid)
            )
            conn.commit()
            counts[category] += 1
            print(f"    [{category.upper():12}] {subject[:60]}")
        except Exception as e:
            print(f"    [ERROR] No se pudo clasificar '{subject[:40]}': {e}")
            conn.execute(
                "UPDATE emails SET category='informativo' WHERE id=?", (eid,)
            )
            conn.commit()

    conn.close()
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
