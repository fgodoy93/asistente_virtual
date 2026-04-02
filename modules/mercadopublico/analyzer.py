"""
Priorización de licitaciones usando el LLM local (Ollama).
Cada licitación recibe: prioridad, puntaje, justificación, acciones y riesgos.
"""
import json
from modules.llm_engine import ask_llm
from modules.logger import get_logger

log = get_logger(__name__)

_SYSTEM = "Responde SOLO con el JSON solicitado, sin texto adicional ni markdown."


def priorizar(licitaciones: list[dict],
              empresa_desc: str,
              capacidades: str) -> list[dict]:
    """
    Analiza y prioriza un lote de licitaciones con el LLM.
    Procesa en bloques de 10 para no saturar el contexto.

    Returns:
        Lista ordenada por puntaje descendente.
    """
    if not licitaciones:
        return []

    resultado: list[dict] = []
    for bloque in _chunks(licitaciones, 10):
        _analizar_bloque(bloque, empresa_desc, capacidades)
        resultado.extend(bloque)

    resultado.sort(key=lambda x: x.get("_puntaje", 0), reverse=True)
    return resultado


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def _analizar_bloque(bloque: list[dict], empresa_desc: str, capacidades: str):
    """Llama al LLM para un bloque y anota los resultados en cada dict."""
    resumen = []
    for i, lic in enumerate(bloque, 1):
        dias = lic.get("_dias_restantes")
        dias_txt = f"{dias}d" if dias is not None else "N/D"
        monto = lic.get("MontoEstimado", "N/D")
        resumen.append(
            f"{i}. [{lic.get('CodigoExterno','?')}] {lic.get('Nombre','')}\n"
            f"   Org: {lic.get('NombreOrganismo','?')}\n"
            f"   Monto: {monto} | Cierre en: {dias_txt}\n"
            f"   Rubro: {lic.get('Rubro1','') or 'N/D'}"
        )

    prompt = f"""Analiza estas licitaciones de Mercado Público Chile y priorizalas para mi empresa.

EMPRESA: {empresa_desc}
CAPACIDADES: {capacidades}

LICITACIONES:
{chr(10).join(resumen)}

Responde con este JSON exacto:
{{
  "items": [
    {{
      "numero": 1,
      "prioridad": "alta|media|baja",
      "puntaje": 1-10,
      "justificacion": "razón breve (max 2 líneas)",
      "acciones": "próximos pasos concretos",
      "riesgos": "principales riesgos o desafíos"
    }}
  ]
}}

Criterios:
- alta (7-10): muy alineada, monto atractivo, plazo suficiente
- media (4-6): parcialmente alineada o con algún desafío
- baja (1-3): fuera de alcance, plazo muy corto o monto no justifica"""

    try:
        respuesta = ask_llm(prompt, system=_SYSTEM)
        inicio = respuesta.find("{")
        fin    = respuesta.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            items = json.loads(respuesta[inicio:fin]).get("items", [])
            for item in items:
                idx = item.get("numero", 0) - 1
                if 0 <= idx < len(bloque):
                    bloque[idx].update({
                        "_prioridad":    item.get("prioridad", "media"),
                        "_puntaje":      item.get("puntaje", 5),
                        "_justificacion": item.get("justificacion", ""),
                        "_acciones":     item.get("acciones", ""),
                        "_riesgos":      item.get("riesgos", ""),
                    })
    except Exception as e:
        log.warning("Error LLM en priorización: %s", e)

    # Valores por defecto para las que no recibieron análisis
    for lic in bloque:
        if "_prioridad" not in lic:
            lic.update({
                "_prioridad": "media", "_puntaje": 5,
                "_justificacion": "Sin análisis (LLM no disponible)",
                "_acciones": "Revisar manualmente",
                "_riesgos": "N/D",
            })
