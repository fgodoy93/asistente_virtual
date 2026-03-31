from dotenv import load_dotenv
import os

load_dotenv()

# Email IMAP
EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 993))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")

# Email SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Ollama LLM local
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# Calendario
ICS_PATH = os.getenv("ICS_PATH", "data/calendar.ics")

# Reporte
REPORT_EMAIL = os.getenv("REPORT_EMAIL", EMAIL_USER)
