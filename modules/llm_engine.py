"""
Abstracción del modelo LLM local via Ollama.
Incluye reintentos con backoff exponencial ante fallos transitorios.
"""
import time
import requests
from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
from modules.logger import get_logger

log = get_logger(__name__)

# Configuración de reintentos
MAX_RETRIES   = 3
BACKOFF_BASE  = 2   # segundos — espera: 2s, 4s, 8s


def ask_llm(prompt: str, system: str = "", model: str = None) -> str:
    """
    Envía un prompt al modelo local y retorna la respuesta.
    Reintenta hasta MAX_RETRIES veces con backoff exponencial.

    Raises:
        RuntimeError: Si todos los reintentos fallan.
    """
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,  # reducido para acelerar respuesta
        }
    }

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.debug("LLM llamada (intento %d/%d, timeout=%ds)", attempt, MAX_RETRIES, OLLAMA_TIMEOUT)
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()["response"].strip()
            log.debug("LLM respuesta recibida (%d chars)", len(result))
            return result

        except requests.exceptions.ConnectionError as e:
            last_error = RuntimeError(
                "No se puede conectar a Ollama. "
                "Asegurate de que este corriendo: ollama serve"
            )
            # Sin reintento en error de conexión — Ollama no está corriendo
            raise last_error

        except requests.exceptions.Timeout as e:
            last_error = e
            wait = BACKOFF_BASE ** attempt
            log.warning("LLM timeout en intento %d. Reintentando en %ds...", attempt, wait)
            time.sleep(wait)

        except requests.exceptions.HTTPError as e:
            last_error = e
            wait = BACKOFF_BASE ** attempt
            log.warning("LLM error HTTP %s en intento %d. Reintentando en %ds...",
                        e.response.status_code, attempt, wait)
            time.sleep(wait)

        except Exception as e:
            last_error = e
            wait = BACKOFF_BASE ** attempt
            log.warning("LLM error inesperado en intento %d: %s. Reintentando en %ds...",
                        attempt, e, wait)
            time.sleep(wait)

    log.error("LLM fallido tras %d intentos: %s", MAX_RETRIES, last_error)
    raise RuntimeError(
        f"El modelo no respondio tras {MAX_RETRIES} intentos. "
        f"Ultimo error: {last_error}"
    )


def check_ollama_available() -> bool:
    """Verifica si Ollama está disponible."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def list_models() -> list[str]:
    """Lista los modelos disponibles en Ollama."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
