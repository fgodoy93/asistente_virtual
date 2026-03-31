"""
Scheduler de Inna — Asistente Virtual.
Ejecuta el pipeline automáticamente en horarios definidos.

Uso:
    python scheduler.py          # Inicia el scheduler en segundo plano
    python scheduler.py --now    # Ejecuta inmediatamente además del horario

Para registrar en Windows Task Scheduler (ejecutar una vez como Admin):
    schtasks /create /tn "AsistenteVirtual" ^
      /tr "python C:\\ruta\\al\\proyecto\\scheduler.py --now" ^
      /sc daily /st 07:00 /ru SYSTEM
"""
import schedule
import time
import sys
import argparse
from datetime import datetime
from main import run


def job():
    """Tarea programada."""
    print(f"\n[SCHEDULER] Ejecutando tarea programada — {datetime.now().strftime('%H:%M')}")
    try:
        run(send_report=True)
    except Exception as e:
        print(f"[SCHEDULER] ERROR en ejecucion: {e}")


def setup_schedule():
    """Define los horarios de ejecución."""
    # Resumen matutino — 7:00 AM
    schedule.every().day.at("07:00").do(job)

    # Revision del mediodia — 13:00
    schedule.every().day.at("13:00").do(job)

    # Resumen de cierre — 18:00
    schedule.every().day.at("18:00").do(job)

    print("Scheduler configurado:")
    print("  - 07:00 — Resumen matutino")
    print("  - 13:00 — Revision del mediodia")
    print("  - 18:00 — Resumen de cierre")
    print("\nPresiona Ctrl+C para detener.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true",
                        help="Ejecutar inmediatamente al iniciar")
    args = parser.parse_args()

    setup_schedule()

    if args.now:
        job()

    while True:
        schedule.run_pending()
        time.sleep(30)
