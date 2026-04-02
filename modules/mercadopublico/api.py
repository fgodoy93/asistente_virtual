"""
Cliente para la API REST de Mercado Público Chile.
https://api.mercadopublico.cl/servicios/v1/publico/
"""
import time
from datetime import datetime, timedelta
import requests

BASE        = "https://api.mercadopublico.cl/servicios/v1/publico"
TIMEOUT     = 120          # La API MP es lenta — 2 minutos
MAX_RETRIES = 3
BACKOFF     = 5            # segundos entre reintentos


def _get(url: str, params: dict) -> requests.Response:
    """GET con reintentos ante timeout."""
    ultimo_error = None
    for intento in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 401:
                raise RuntimeError("API Key inválida (401). Verifica MP_API_KEY en .env")
            r.raise_for_status()
            return r
        except RuntimeError:
            raise
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Sin conexión a api.mercadopublico.cl")
        except requests.exceptions.Timeout as e:
            ultimo_error = e
            if intento < MAX_RETRIES:
                time.sleep(BACKOFF * intento)
        except Exception as e:
            ultimo_error = e
            if intento < MAX_RETRIES:
                time.sleep(BACKOFF)

    raise RuntimeError(
        f"La API no respondió tras {MAX_RETRIES} intentos. "
        f"Mercado Público puede estar lento — intenta más tarde."
    )


def fetch_activas(ticket: str, dias: int = 3) -> list[dict]:
    """
    Trae licitaciones activas de los últimos N días.
    Deduplica por CodigoExterno.
    """
    vistas: set[str] = set()
    resultado: list[dict] = []

    for d in range(dias):
        fecha = (datetime.now() - timedelta(days=d)).strftime("%d%m%Y")
        try:
            r = _get(
                f"{BASE}/licitaciones.json",
                {"ticket": ticket, "estado": "activas", "fecha": fecha},
            )
            for lic in r.json().get("Listado", []):
                cod = lic.get("CodigoExterno", "")
                if cod and cod not in vistas:
                    vistas.add(cod)
                    resultado.append(lic)
        except RuntimeError:
            raise

    return resultado


def fetch_detalle(ticket: str, codigo: str) -> dict:
    """Detalle completo de una licitación. Retorna {} si falla."""
    try:
        r = _get(
            f"{BASE}/licitaciones.json",
            {"ticket": ticket, "codigo": codigo},
        )
        listado = r.json().get("Listado", [])
        return listado[0] if listado else {}
    except Exception:
        return {}
