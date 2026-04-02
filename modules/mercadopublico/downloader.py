"""
Descarga los documentos de bases de una licitación.
Guarda en data/bases/{CODIGO}/
"""
import re
import json
from pathlib import Path

import requests

from modules.logger import get_logger

log = get_logger(__name__)
BASES_DIR = Path("data/bases")
TIMEOUT   = 60


def descargar(codigo: str, detalle: dict) -> list[str]:
    """
    Descarga todos los adjuntos de una licitación.

    Args:
        codigo:  CodigoExterno de la licitación.
        detalle: Dict completo retornado por api.fetch_detalle().

    Returns:
        Lista de rutas a los archivos descargados.
    """
    carpeta = BASES_DIR / _sanitizar(codigo)
    carpeta.mkdir(parents=True, exist_ok=True)

    # Guardar metadata
    meta = carpeta / "metadata.json"
    if not meta.exists():
        meta.write_text(json.dumps(detalle, ensure_ascii=False, indent=2), encoding="utf-8")

    # Extraer adjuntos (la API puede retornarlos de varias formas)
    raw = detalle.get("Adjuntos", {})
    if isinstance(raw, dict):
        adjuntos = raw.get("Listado", [])
    elif isinstance(raw, list):
        adjuntos = raw
    else:
        adjuntos = []

    if not adjuntos:
        # Sin adjuntos: guardar referencia al portal
        ref = carpeta / "ver_en_portal.txt"
        ref.write_text(
            f"Ver en Mercado Público:\n"
            f"https://www.mercadopublico.cl/Procurement/Modules/RFB/"
            f"DetailsAcquisition.aspx?idlicitacion={codigo}\n",
            encoding="utf-8",
        )
        return [str(ref)]

    descargados = []
    for adj in adjuntos:
        url    = adj.get("URL") or adj.get("Url") or ""
        nombre = _sanitizar(adj.get("Nombre") or adj.get("NombreArchivo") or "documento")
        if not url:
            continue

        dest = carpeta / nombre
        if dest.exists():
            descargados.append(str(dest))
            continue

        try:
            resp = requests.get(url, timeout=TIMEOUT, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            size_kb = dest.stat().st_size // 1024
            log.info("Descargado: %s (%d KB)", nombre, size_kb)
            descargados.append(str(dest))
        except Exception as e:
            log.warning("Error descargando %s: %s", nombre, e)

    return descargados


def _sanitizar(nombre: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]', "_", nombre)[:80]
