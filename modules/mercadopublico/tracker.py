"""
Seguimiento de licitaciones en SQLite.
Evita revisar dos veces la misma licitación entre ejecuciones.

Estados posibles:
    nueva      → detectada, pendiente de revisión
    revisada   → el usuario la revisó en el menú
    descartada → el usuario la descartó manualmente
    ofertando  → se decidió preparar oferta
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/licitaciones.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS licitaciones (
    codigo          TEXT PRIMARY KEY,
    nombre          TEXT,
    organismo       TEXT,
    monto           REAL,
    fecha_cierre    TEXT,
    dias_restantes  INTEGER,
    prioridad       TEXT,
    puntaje         INTEGER,
    justificacion   TEXT,
    acciones        TEXT,
    riesgos         TEXT,
    fecha_detectada TEXT,
    estado          TEXT DEFAULT 'nueva'
);
"""


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init():
    """Crea la base de datos y la tabla si no existen."""
    with _conn() as con:
        con.executescript(_SCHEMA)


def codigos_conocidos() -> set[str]:
    """Retorna todos los códigos ya registrados (independiente del estado)."""
    with _conn() as con:
        rows = con.execute("SELECT codigo FROM licitaciones").fetchall()
    return {r["codigo"] for r in rows}


def filtrar_nuevas(licitaciones: list[dict]) -> list[dict]:
    """Descarta las licitaciones que ya están en el historial."""
    conocidos = codigos_conocidos()
    return [l for l in licitaciones if l.get("CodigoExterno", "") not in conocidos]


def registrar_lote(licitaciones: list[dict]):
    """
    Inserta un lote de licitaciones priorizadas.
    Ignora duplicados (INSERT OR IGNORE).
    """
    ahora = datetime.now().isoformat(timespec="seconds")
    filas = []
    for l in licitaciones:
        filas.append((
            l.get("CodigoExterno", ""),
            l.get("Nombre", ""),
            l.get("NombreOrganismo", ""),
            _to_float(l.get("MontoEstimado")),
            str(l.get("FechaCierre", "")),
            l.get("_dias_restantes"),
            l.get("_prioridad", ""),
            l.get("_puntaje", 0),
            l.get("_justificacion", ""),
            l.get("_acciones", ""),
            l.get("_riesgos", ""),
            ahora,
        ))
    with _conn() as con:
        con.executemany(
            """INSERT OR IGNORE INTO licitaciones
               (codigo, nombre, organismo, monto, fecha_cierre, dias_restantes,
                prioridad, puntaje, justificacion, acciones, riesgos, fecha_detectada)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            filas,
        )


def marcar_estado(codigo: str, estado: str):
    """Actualiza el estado de una licitación."""
    with _conn() as con:
        con.execute(
            "UPDATE licitaciones SET estado=? WHERE codigo=?",
            (estado, codigo),
        )


def get_pendientes() -> list[dict]:
    """Licitaciones en estado 'nueva', ordenadas por puntaje desc."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM licitaciones WHERE estado='nueva' ORDER BY puntaje DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_ofertando() -> list[dict]:
    """Licitaciones marcadas para ofertar."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM licitaciones WHERE estado='ofertando' ORDER BY fecha_cierre"
        ).fetchall()
    return [dict(r) for r in rows]


def get_historial() -> list[dict]:
    """Todas las licitaciones, ordenadas por fecha de detección."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM licitaciones ORDER BY fecha_detectada DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def resumen() -> dict:
    """Conteo por estado."""
    with _conn() as con:
        rows = con.execute(
            "SELECT estado, COUNT(*) as n FROM licitaciones GROUP BY estado"
        ).fetchall()
    return {r["estado"]: r["n"] for r in rows}


def _to_float(valor) -> float | None:
    if valor is None:
        return None
    import re
    limpio = re.sub(r"[^\d.]", "", str(valor).replace(",", "."))
    try:
        return float(limpio) if limpio else None
    except ValueError:
        return None
