"""
Tests unitarios para el lector de calendario.
"""
import pytest
import tempfile
import os
from datetime import date, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.calendar_reader import detect_conflicts, format_events_summary


# Fixture: archivo .ics mínimo válido
ICS_TEMPLATE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
{events}
END:VCALENDAR"""

ICS_EVENT = """BEGIN:VEVENT
SUMMARY:{summary}
DTSTART:{start}
DTEND:{end}
END:VEVENT"""


def make_ics(events: list[dict]) -> str:
    """Genera contenido .ics desde una lista de eventos."""
    event_blocks = "\n".join([
        ICS_EVENT.format(**e) for e in events
    ])
    return ICS_TEMPLATE.format(events=event_blocks)


class TestDetectConflicts:

    def test_sin_conflictos(self):
        events = [
            {"summary": "A", "start": "2026-04-01 09:00", "end": "2026-04-01 10:00", "start_raw": "2026-04-01 09:00"},
            {"summary": "B", "start": "2026-04-01 10:00", "end": "2026-04-01 11:00", "start_raw": "2026-04-01 10:00"},
        ]
        assert detect_conflicts(events) == []

    def test_con_conflicto(self):
        events = [
            {"summary": "A", "start": "2026-04-01 09:00", "end": "2026-04-01 10:30", "start_raw": "2026-04-01 09:00"},
            {"summary": "B", "start": "2026-04-01 10:00", "end": "2026-04-01 11:00", "start_raw": "2026-04-01 10:00"},
        ]
        conflicts = detect_conflicts(events)
        assert len(conflicts) == 1
        assert "A" in conflicts[0]
        assert "B" in conflicts[0]

    def test_lista_vacia(self):
        assert detect_conflicts([]) == []

    def test_un_solo_evento(self):
        events = [{"summary": "Solo", "start": "2026-04-01 09:00", "end": "2026-04-01 10:00", "start_raw": "2026-04-01 09:00"}]
        assert detect_conflicts(events) == []


class TestFormatEventsSummary:

    def test_sin_eventos(self):
        result = format_events_summary([])
        assert "No hay eventos" in result

    def test_con_eventos(self):
        events = [
            {"start": "01/04/2026 09:00", "summary": "Reunion", "location": "Sala A"},
            {"start": "02/04/2026 14:00", "summary": "Demo",    "location": ""},
        ]
        result = format_events_summary(events)
        assert "Reunion" in result
        assert "Sala A" in result
        assert "Demo" in result

    def test_evento_sin_location(self):
        events = [{"start": "01/04/2026", "summary": "Evento", "location": ""}]
        result = format_events_summary(events)
        assert "Evento" in result
        assert "()" not in result  # No debe mostrar paréntesis vacíos
