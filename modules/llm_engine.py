"""
Abstracción del modelo LLM local via Ollama.
Documentación Ollama: https://github.com/ollama/ollama
"""
import requests
from config import OLLAMA_URL, OLLAMA_MODEL


def ask_llm(prompt: str, system: str = "", model: str = None) -> str:
    """
    Envía un prompt al modelo local y retorna la respuesta como texto.

    Args:
        prompt: El texto de entrada para el modelo.
        system: Instrucción de sistema (rol/contexto del asistente).
        model: Sobreescribe el modelo por defecto si se especifica.

    Returns:
        Respuesta del modelo como string.

    Raises:
        RuntimeError: Si Ollama no está corriendo o hay error de red.
    """
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        return response.json()["response"].strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "No se puede conectar a Ollama. "
            "Asegurate de que este corriendo: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("El modelo tardo demasiado en responder. Intenta con un modelo mas liviano.")
    except Exception as e:
        raise RuntimeError(f"Error en LLM: {e}")


def check_ollama_available() -> bool:
    """Verifica si Ollama esta disponible."""
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
