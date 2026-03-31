"""
Módulo de lectura de correos via IMAP.
Compatible con Gmail, Outlook y cualquier proveedor IMAP estándar.
"""
import imaplib
import email
import sqlite3
from email.header import decode_header
from datetime import datetime
from pathlib import Path
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS


DB_PATH = "data/emails.db"


def init_db():
    """Inicializa la base de datos SQLite si no existe."""
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id          TEXT PRIMARY KEY,
            subject     TEXT,
            sender      TEXT,
            date        TEXT,
            body        TEXT,
            category    TEXT DEFAULT 'sin_clasificar',
            reply       TEXT DEFAULT '',
            processed   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def decode_str(value: str) -> str:
    """Decodifica encabezados de correo (soporte UTF-8, Latin-1, etc.)."""
    if value is None:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded).strip()


def get_body(msg) -> str:
    """Extrae el cuerpo en texto plano del mensaje."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition  = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    continue
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())

    # Limitar tamaño para no saturar el LLM
    return body[:3000].strip()


def fetch_emails(limit: int = 30, folder: str = "INBOX") -> list[dict]:
    """
    Descarga correos no leídos via IMAP y los guarda en SQLite.

    Args:
        limit: Cantidad máxima de correos a descargar.
        folder: Carpeta IMAP (por defecto INBOX).

    Returns:
        Lista de diccionarios con los datos de cada correo.
    """
    conn = init_db()
    emails_list = []

    print(f"  Conectando a {EMAIL_HOST}...")
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select(folder)

        # Buscar correos no leídos
        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()

        if not ids:
            print("  No hay correos nuevos.")
            mail.logout()
            conn.close()
            return []

        # Tomar solo los más recientes
        ids = ids[-limit:]
        print(f"  {len(ids)} correos nuevos encontrados.")

        for eid in ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            email_id = msg.get("Message-ID", f"id_{eid.decode()}")
            subject  = decode_str(msg.get("Subject", "(sin asunto)"))
            sender   = decode_str(msg.get("From", ""))
            date_str = msg.get("Date", str(datetime.now()))
            body     = get_body(msg)

            # Evitar duplicados
            exists = conn.execute(
                "SELECT 1 FROM emails WHERE id=?", (email_id,)
            ).fetchone()

            if not exists:
                conn.execute(
                    """INSERT INTO emails (id, subject, sender, date, body)
                       VALUES (?,?,?,?,?)""",
                    (email_id, subject, sender, date_str, body)
                )
                conn.commit()

            emails_list.append({
                "id":      email_id,
                "subject": subject,
                "sender":  sender,
                "date":    date_str,
                "body":    body
            })

        mail.logout()
        print(f"  {len(emails_list)} correos guardados en BD.")

    except imaplib.IMAP4.error as e:
        raise RuntimeError(
            f"Error de autenticacion IMAP: {e}\n"
            "Para Gmail: activa 'App Passwords' en tu cuenta Google."
        )
    except Exception as e:
        raise RuntimeError(f"Error al conectar al correo: {e}")
    finally:
        conn.close()

    return emails_list


def get_unprocessed_emails() -> list[dict]:
    """Retorna todos los correos que no han sido procesados aún."""
    conn = init_db()
    rows = conn.execute(
        "SELECT id, subject, sender, date, body, category FROM emails WHERE processed=0"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "subject": r[1], "sender": r[2],
         "date": r[3], "body": r[4], "category": r[5]}
        for r in rows
    ]


def mark_as_processed(email_ids: list[str]):
    """Marca correos como procesados."""
    conn = init_db()
    for eid in email_ids:
        conn.execute("UPDATE emails SET processed=1 WHERE id=?", (eid,))
    conn.commit()
    conn.close()
