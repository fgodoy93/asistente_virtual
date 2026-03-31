"""
Módulo de lectura de calendario.
Soporta archivos .ics locales (Google Calendar, Outlook, Apple Calendar).
"""
from icalendar import Calendar
from datetime import datetime, date, timedelta, timezone
from pathlib import Path


def read_ics(filepath: str, days_ahead: int = 7) -> list[dict]:
    """
    Lee eventos desde un archivo .ics para los próximos N días.

    Args:
        filepath: Ruta al archivo .ics.
        days_ahead: Cuántos días hacia adelante buscar (default 7).

    Returns:
        Lista de eventos ordenados por fecha.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo: {filepath}\n"
            "Exporta tu calendario desde Google Calendar:\n"
            "  Settings > Export > descarga el .ics y copialo en data/calendar.ics"
        )

    cal = Calendar.from_ical(path.read_bytes())

    today      = date.today()
    limit_date = today + timedelta(days=days_ahead)
    events     = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart_prop = component.get("DTSTART")
        dtend_prop   = component.get("DTEND")

        if dtstart_prop is None:
            continue

        dtstart = dtstart_prop.dt
        dtend   = dtend_prop.dt if dtend_prop else dtstart

        # Normalizar a date para comparación
        if isinstance(dtstart, datetime):
            event_date = dtstart.date()
            # Convertir a string legible con hora
            start_str = dtstart.strftime("%d/%m/%Y %H:%M")
            end_str   = dtend.strftime("%d/%m/%Y %H:%M") if isinstance(dtend, datetime) else str(dtend)
        else:
            event_date = dtstart
            start_str  = dtstart.strftime("%d/%m/%Y")
            end_str    = dtend.strftime("%d/%m/%Y") if isinstance(dtend, date) else str(dtend)

        # Filtrar por rango de fechas
        if not (today <= event_date <= limit_date):
            continue

        events.append({
            "summary":     str(component.get("SUMMARY",     "Sin titulo")),
            "start":       start_str,
            "end":         end_str,
            "start_raw":   str(dtstart),
            "location":    str(component.get("LOCATION",    "")),
            "description": str(component.get("DESCRIPTION", ""))[:300],
            "organizer":   str(component.get("ORGANIZER",   "")),
        })

    # Ordenar por fecha de inicio
    events.sort(key=lambda x: x["start_raw"])
    return events


def detect_conflicts(events: list[dict]) -> list[str]:
    """
    Detecta eventos con horarios superpuestos.

    Returns:
        Lista de strings describiendo cada conflicto encontrado.
    """
    conflicts = []
    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            a = events[i]
            b = events[j]
            # Comparar usando start_raw
            if a["start_raw"] < b["end"] and b["start_raw"] < a["end"]:
                conflicts.append(
                    f"CONFLICTO: '{a['summary']}' ({a['start']}) "
                    f"se superpone con '{b['summary']}' ({b['start']})"
                )
    return conflicts


def get_today_events(filepath: str) -> list[dict]:
    """Retorna solo los eventos de hoy."""
    try:
        all_events = read_ics(filepath, days_ahead=0)
        today_str  = date.today().strftime("%d/%m/%Y")
        return [e for e in all_events if e["start"].startswith(today_str)]
    except FileNotFoundError:
        return []


def format_events_summary(events: list[dict]) -> str:
    """Formatea la lista de eventos como texto legible."""
    if not events:
        return "No hay eventos programados para los proximos dias."

    lines = []
    for ev in events:
        line = f"• {ev['start']} — {ev['summary']}"
        if ev["location"]:
            line += f" ({ev['location']})"
        lines.append(line)
    return "\n".join(lines)
