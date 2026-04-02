"""
Filtros de licitaciones:
  - por_perfil   → rubros y palabras clave del .env
  - dinamicos    → monto, plazo de cierre, requerimientos técnicos
"""
import re
from datetime import datetime


# ── Normalización ────────────────────────────────────────────────────────────

def _norm(texto: str) -> str:
    tabla = str.maketrans(
        "áéíóúàèìòùäëïöüÁÉÍÓÚÀÈÌÒÙ",
        "aeiouaeiouaeiouAEIOUAEIOU",
    )
    return (texto or "").lower().translate(tabla)


def _texto_lic(lic: dict) -> str:
    return _norm(" ".join([
        lic.get("Nombre", ""),
        lic.get("Descripcion", "") or "",
        lic.get("Rubro1", "") or "",
        lic.get("Rubro2", "") or "",
        lic.get("Rubro3", "") or "",
    ]))


# ── Filtro por perfil ────────────────────────────────────────────────────────

def por_perfil(licitaciones: list[dict],
               rubros: list[str],
               keywords: list[str]) -> list[dict]:
    """
    Conserva solo licitaciones que coincidan con al menos un
    rubro o keyword del perfil configurado.
    Si ambas listas están vacías retorna todo (sin filtrar).
    """
    r_norm = [_norm(r) for r in rubros   if r.strip()]
    k_norm = [_norm(k) for k in keywords if k.strip()]

    if not r_norm and not k_norm:
        return licitaciones

    resultado = []
    for lic in licitaciones:
        texto = _texto_lic(lic)
        if any(r in texto for r in r_norm) or any(k in texto for k in k_norm):
            resultado.append(lic)
    return resultado


# ── Helpers de parseo ────────────────────────────────────────────────────────

def _parse_monto(valor) -> float | None:
    limpio = re.sub(r"[^\d.]", "", str(valor or "").replace(",", "."))
    try:
        return float(limpio) if limpio else None
    except ValueError:
        return None


def _parse_cierre(valor: str | None) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor or "")[:19], fmt)
        except ValueError:
            continue
    return None


# ── Filtros dinámicos ────────────────────────────────────────────────────────

def dinamicos(licitaciones: list[dict],
              monto_min: int = 0,
              monto_max: int = 0,
              dias_cierre_min: int = 0,
              dias_cierre_max: int = 0,
              reqs_tecnicos: list[str] = None) -> tuple[list[dict], dict]:
    """
    Aplica filtros de monto, plazo y requerimientos técnicos.

    Returns:
        (lista_filtrada, stats_de_descarte)
    """
    reqs = [_norm(r) for r in (reqs_tecnicos or []) if r.strip()]
    ahora = datetime.now()
    pasaron, desc = [], {"monto": 0, "fecha": 0, "reqs": 0}

    for lic in licitaciones:
        # Monto
        monto = _parse_monto(lic.get("MontoEstimado"))
        if monto is not None:
            if monto_min > 0 and monto < monto_min:
                desc["monto"] += 1
                continue
            if monto_max > 0 and monto > monto_max:
                desc["monto"] += 1
                continue

        # Plazo de cierre
        cierre = _parse_cierre(lic.get("FechaCierre"))
        dias = int((cierre - ahora).days) if cierre else None
        lic["_dias_restantes"] = dias

        if dias is not None:
            if dias_cierre_min > 0 and dias < dias_cierre_min:
                desc["fecha"] += 1
                continue
            if dias_cierre_max > 0 and dias > dias_cierre_max:
                desc["fecha"] += 1
                continue

        # Requerimientos técnicos
        if reqs:
            texto = _texto_lic(lic)
            encontrados = [r for r in reqs if r in texto]
            lic["_reqs_encontrados"] = encontrados
            if not encontrados:
                desc["reqs"] += 1
                continue

        pasaron.append(lic)

    return pasaron, desc
