"""
Generador de respuestas sugeridas para correos via LLM.
También maneja el envío de correos via SMTP.
"""
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from modules.llm_engine import ask_llm
from modules.email_reader import DB_PATH
from config import EMAIL_USER, EMAIL_PASS, SMTP_HOST, SMTP_PORT

SYSTEM_PROMPT = """Eres un asistente profesional que redacta respuestas de correo electronico.
Reglas:
- Responde en el MISMO idioma del correo original
- Tono: profesional, cordial y conciso
- No inventes informacion que no esta en el correo original
- Incluye un saludo apropiado y una despedida formal
- Maximo 150 palabras
- No agregues notas ni meta-comentarios sobre la respuesta"""


def generate_reply(subject: str, body: str, sender: str) -> str:
    """
    Genera una respuesta sugerida para un correo.

    Args:
        subject: Asunto del correo original.
        body: Cuerpo del correo original.
        sender: Remitente del correo.

    Returns:
        Texto de la respuesta sugerida.
    """
    prompt = f"""De: {sender}
Asunto: {subject}
Contenido del correo:
{body[:1500]}

Redacta una respuesta profesional:"""
    return ask_llm(prompt, system=SYSTEM_PROMPT)


def generate_and_save_replies(categories: list[str] = None):
    """
    Genera respuestas para correos urgentes e importantes y las guarda en BD.

    Args:
        categories: Lista de categorías para las que generar respuestas.
                   Por defecto: urgente e importante.
    """
    if categories is None:
        categories = ["urgente", "importante"]

    placeholders = ",".join("?" * len(categories))
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        f"""SELECT id, subject, sender, body FROM emails
            WHERE category IN ({placeholders}) AND reply='' AND processed=0""",
        categories
    ).fetchall()

    if not rows:
        print("  No hay correos que requieran respuesta sugerida.")
        conn.close()
        return []

    print(f"  Generando {len(rows)} respuestas sugeridas...")
    replies = []

    for eid, subject, sender, body in rows:
        try:
            reply = generate_reply(subject, body, sender)
            conn.execute(
                "UPDATE emails SET reply=? WHERE id=?", (reply, eid)
            )
            conn.commit()
            replies.append({"subject": subject, "sender": sender, "reply": reply})
            print(f"    Respuesta generada para: {subject[:50]}")
        except Exception as e:
            print(f"    [ERROR] No se pudo generar respuesta para '{subject[:40]}': {e}")

    conn.close()
    return replies


def send_email(to: str, subject: str, body: str):
    """
    Envía un correo via SMTP.

    Args:
        to: Destinatario.
        subject: Asunto.
        body: Cuerpo del correo (texto plano o HTML).
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_USER
    msg["To"]      = to

    msg.attach(MIMEText(body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to, msg.as_string())

    print(f"  Correo enviado a {to}: {subject}")
