"""
Orquestador principal de Inna — Asistente Virtual Local.
Ejecuta el pipeline completo: correos → clasificación → calendario → reporte.

Uso:
    python main.py              # Ejecución completa
    python main.py --check      # Solo verifica conexiones
    python main.py --no-email   # Sin envío de reporte por correo
"""
import sys
import os
import argparse
from datetime import datetime

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.llm_engine       import check_ollama_available, list_models
from modules.email_reader     import fetch_emails, get_unprocessed_emails, mark_as_processed
from modules.email_classifier import classify_pending
from modules.email_responder  import generate_and_save_replies, send_email
from modules.calendar_reader  import read_ics, detect_conflicts, format_events_summary
from modules.report_generator import build_report
from config import ICS_PATH, REPORT_EMAIL


def print_header():
    print("\n" + "="*55)
    print("   INNA — Asistente Virtual Local — by fgodoy93")
    print(f"   {datetime.now().strftime('%A %d/%m/%Y %H:%M')}")
    print("="*55)


def check_connections():
    """Verifica que todos los servicios estén disponibles."""
    print("\n[CHECK] Verificando servicios...")

    # Ollama
    if check_ollama_available():
        models = list_models()
        print(f"  ✓ Ollama disponible. Modelos: {', '.join(models) or 'ninguno'}")
    else:
        print("  ✗ Ollama NO disponible. Ejecuta: ollama serve")
        print("    Descarga: https://ollama.com/download/windows")
        return False

    # Calendario
    if os.path.exists(ICS_PATH):
        print(f"  ✓ Calendario encontrado: {ICS_PATH}")
    else:
        print(f"  ⚠ Calendario no encontrado: {ICS_PATH}")
        print("    Exporta tu .ics desde Google Calendar y copialo en data/calendar.ics")

    print("\n  Para configurar correo, edita el archivo .env")
    print("  Gmail necesita una 'App Password' (no tu contraseña normal)")
    return True


def run(send_report: bool = True):
    """Pipeline completo del asistente."""
    print_header()

    # ── PASO 1: Verificar Ollama ──────────────────────────
    print("\n[1/5] Verificando LLM local...")
    if not check_ollama_available():
        print("  ERROR: Ollama no esta disponible.")
        print("  Instala y ejecuta: ollama serve")
        print("  Luego descarga un modelo: ollama pull mistral")
        sys.exit(1)
    print("  OK — Ollama disponible")

    # ── PASO 2: Descargar correos ─────────────────────────
    print("\n[2/5] Descargando correos nuevos...")
    try:
        new_emails = fetch_emails(limit=30)
        print(f"  {len(new_emails)} correos nuevos descargados")
    except RuntimeError as e:
        print(f"  ADVERTENCIA: {e}")
        print("  Continuando sin correos nuevos...")

    # ── PASO 3: Clasificar correos ────────────────────────
    print("\n[3/5] Clasificando correos con IA...")
    counts = classify_pending()
    if counts:
        for cat, n in counts.items():
            if n > 0:
                print(f"    {cat.upper()}: {n}")

    # ── PASO 4: Generar respuestas sugeridas ──────────────
    print("\n[4/5] Generando respuestas para correos urgentes/importantes...")
    generate_and_save_replies(categories=["urgente", "importante"])

    # ── PASO 5: Leer calendario ───────────────────────────
    print("\n[5/5] Leyendo calendario...")
    events    = []
    conflicts = []
    try:
        events    = read_ics(ICS_PATH, days_ahead=7)
        conflicts = detect_conflicts(events)
        print(f"  {len(events)} eventos encontrados")
        if conflicts:
            print(f"  ⚠ {len(conflicts)} conflictos detectados")
        if events:
            print(format_events_summary(events))
    except FileNotFoundError as e:
        print(f"  {e}")

    # ── REPORTE ───────────────────────────────────────────
    print("\n[+] Generando reporte consolidado...")
    try:
        output_files = build_report(events, conflicts)

        # Marcar correos como procesados
        emails = get_unprocessed_emails()
        mark_as_processed([e["id"] for e in emails])

        print("\n" + "="*55)
        print("  REPORTE GENERADO:")
        for fmt, path in output_files.items():
            print(f"    [{fmt.upper()}] {path}")
        print("="*55)

        # Enviar por correo si corresponde
        if send_report and "html" in output_files and REPORT_EMAIL:
            try:
                html_content = open(output_files["html"], encoding="utf-8").read()
                fecha = datetime.now().strftime("%d/%m/%Y")
                send_email(
                    to=REPORT_EMAIL,
                    subject=f"Informe Diario — {fecha}",
                    body=html_content
                )
            except Exception as e:
                print(f"  [ADVERTENCIA] No se pudo enviar el reporte: {e}")

    except Exception as e:
        print(f"  ERROR generando reporte: {e}")
        raise

    print("\n  Asistente completado exitosamente.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inna — Asistente Virtual Local")
    parser.add_argument("--check",    action="store_true", help="Solo verificar conexiones")
    parser.add_argument("--no-email", action="store_true", help="No enviar reporte por correo")
    args = parser.parse_args()

    if args.check:
        check_connections()
    else:
        run(send_report=not args.no_email)
