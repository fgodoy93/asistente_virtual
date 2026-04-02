"""
Inna — Revisión de Licitaciones (Mercado Público Chile)
Ejecutar: python licitaciones.py

Entry point interactivo, independiente de main.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from modules.mercadopublico import api, filters, analyzer, tracker, downloader
from modules.llm_engine import check_ollama_available

# ── Configuración desde .env ──────────────────────────────────────────────────
API_KEY       = os.getenv("MP_API_KEY", "")
RUBROS        = [r.strip() for r in os.getenv("MP_RUBROS", "").split(",") if r.strip()]
KEYWORDS      = [k.strip() for k in os.getenv("MP_KEYWORDS", "").split(",") if k.strip()]
EMPRESA_DESC  = os.getenv("MP_EMPRESA_DESC", "(sin descripción — configura MP_EMPRESA_DESC en .env)")
CAPACIDADES   = os.getenv("MP_CAPACIDADES",  "(sin capacidades — configura MP_CAPACIDADES en .env)")
MONTO_MIN     = int(os.getenv("MP_MONTO_MIN", 0))
MONTO_MAX     = int(os.getenv("MP_MONTO_MAX", 0))
DIAS_MIN      = int(os.getenv("MP_DIAS_CIERRE_MIN", 3))
DIAS_MAX      = int(os.getenv("MP_DIAS_CIERRE_MAX", 90))
REQS          = [r.strip() for r in os.getenv("MP_REQS_TECNICOS", "").split(",") if r.strip()]


# ── UI helpers ────────────────────────────────────────────────────────────────

COLORES = {
    "alta":   "\033[91m",   # rojo
    "media":  "\033[93m",   # amarillo
    "baja":   "\033[90m",   # gris
    "ok":     "\033[92m",   # verde
    "azul":   "\033[94m",
    "negrita":"\033[1m",
    "reset":  "\033[0m",
}

ESTADO_COLOR = {
    "nueva":      "\033[94m",
    "revisada":   "\033[92m",
    "ofertando":  "\033[95m",
    "descartada": "\033[90m",
}

def c(texto: str, clave: str) -> str:
    return f"{COLORES.get(clave,'')}{texto}{COLORES['reset']}"

def limpiar():
    os.system("cls" if os.name == "nt" else "clear")

def separador(ancho: int = 54):
    print("─" * ancho)

def cabecera(titulo: str = ""):
    limpiar()
    print(c("╔══════════════════════════════════════════════════════╗", "azul"))
    print(c("║   INNA  ·  Licitaciones — Mercado Público Chile      ║", "azul"))
    print(c("╚══════════════════════════════════════════════════════╝", "azul"))
    if titulo:
        print(f"\n  {c(titulo, 'negrita')}")
    print()

def pausar():
    input("\n  Presiona Enter para continuar...")

def pedir_opcion(opciones: list[str]) -> str:
    while True:
        op = input("  › ").strip()
        if op in opciones:
            return op
        print(f"  Opción inválida. Opciones: {', '.join(opciones)}")


# ── Pantallas ─────────────────────────────────────────────────────────────────

def pantalla_menu_principal() -> str:
    resumen = tracker.resumen()
    nuevas    = resumen.get("nueva", 0)
    ofertando = resumen.get("ofertando", 0)

    cabecera()
    separador()
    print(f"  {c('[1]', 'azul')}  Buscar nuevas licitaciones")
    print(f"  {c('[2]', 'azul')}  Ver pendientes          "
          + (c(f"  ({nuevas} sin revisar)", "alta") if nuevas else ""))
    print(f"  {c('[3]', 'azul')}  Licitaciones a ofertar  "
          + (c(f"  ({ofertando})", "ok") if ofertando else ""))
    print(f"  {c('[4]', 'azul')}  Descargar bases")
    print(f"  {c('[5]', 'azul')}  Historial completo")
    print(f"  {c('[6]', 'azul')}  Filtros activos")
    print(f"  {c('[0]', 'azul')}  Salir")
    separador()
    return pedir_opcion(["0", "1", "2", "3", "4", "5", "6"])


def pantalla_buscar():
    """Busca nuevas licitaciones, filtra, prioriza y guarda las nuevas."""
    cabecera("Buscando nuevas licitaciones...")

    if not API_KEY:
        print(c("  ✗ MP_API_KEY no configurada en .env", "alta"))
        pausar()
        return

    # 1 — Fetch
    print("  Consultando API Mercado Público (puede tardar hasta 2 min)...")
    try:
        todas = api.fetch_activas(API_KEY, dias=3)
    except RuntimeError as e:
        print(c(f"  ✗ {e}", "alta"))
        pausar()
        return
    print(f"  {c(str(len(todas)), 'ok')} licitaciones activas en los últimos 3 días")

    # 2 — Filtrar nuevas (no vistas)
    nuevas = tracker.filtrar_nuevas(todas)
    ya_vistas = len(todas) - len(nuevas)
    print(f"  {c(str(ya_vistas), 'azul')} ya revisadas anteriormente → omitidas")
    print(f"  {c(str(len(nuevas)), 'ok')} licitaciones nuevas para analizar")

    if not nuevas:
        print(c("\n  No hay licitaciones nuevas. Vuelve más tarde.", "azul"))
        pausar()
        return

    # 3 — Filtro por perfil
    por_perfil = filters.por_perfil(nuevas, RUBROS, KEYWORDS)
    print(f"\n  Filtro de perfil (rubros/keywords): "
          f"{c(str(len(por_perfil)), 'ok')} relevantes de {len(nuevas)}")

    if not por_perfil:
        print(c("  Ninguna coincide con tu perfil.", "azul"))
        pausar()
        return

    # 4 — Filtros dinámicos
    filtradas, desc = filters.dinamicos(
        por_perfil, MONTO_MIN, MONTO_MAX, DIAS_MIN, DIAS_MAX, REQS
    )
    print(f"  Filtros dinámicos: {c(str(len(filtradas)), 'ok')} pasan  "
          f"(monto: {desc['monto']}  fecha: {desc['fecha']}  reqs: {desc['reqs']} descartadas)")

    if not filtradas:
        print(c("  Ninguna supera los filtros dinámicos.", "azul"))
        pausar()
        return

    # 5 — Priorización LLM
    ollama_ok = check_ollama_available()
    if ollama_ok:
        print(f"\n  Priorizando {len(filtradas)} licitaciones con IA...")
        priorizadas = analyzer.priorizar(filtradas, EMPRESA_DESC, CAPACIDADES)
    else:
        print(c("  ⚠ Ollama no disponible — sin priorización IA", "media"))
        priorizadas = filtradas

    # 6 — Guardar en tracker
    tracker.registrar_lote(priorizadas)
    print(c(f"\n  ✓ {len(priorizadas)} licitaciones guardadas.", "ok"))

    # Mostrar resumen rápido
    separador()
    for lic in priorizadas[:5]:
        prio = lic.get("_prioridad", "?")
        print(f"  {c(f'[{prio.upper()}]', prio):20s} {lic.get('Nombre','')[:55]}")
    if len(priorizadas) > 5:
        print(f"  ... y {len(priorizadas)-5} más. Usa [2] para ver todas.")

    pausar()


def pantalla_pendientes():
    """Muestra licitaciones pendientes de revisión."""
    while True:
        pendientes = tracker.get_pendientes()
        cabecera(f"Pendientes de revisión  ({len(pendientes)})")

        if not pendientes:
            print(c("  No hay licitaciones pendientes.", "azul"))
            pausar()
            return

        for i, lic in enumerate(pendientes, 1):
            prio  = lic.get("prioridad", "?")
            nombre = lic.get("nombre", "")[:55]
            dias   = lic.get("dias_restantes")
            dias_txt = f"{dias}d" if dias is not None else "N/D"
            monto  = lic.get("monto")
            monto_txt = f"${monto:,.0f}" if monto else "N/D"
            print(f"  {c(str(i),'azul'):>4}.  {c(f'[{prio.upper()}]', prio):20s}"
                  f"  {nombre}")
            print(f"         {lic.get('organismo','')[:45]}"
                  f"  |  Cierre: {dias_txt}  |  Monto: {monto_txt}")
            print()

        separador()
        print("  Escribe el número para ver detalle  |  [0] Volver")
        opciones = ["0"] + [str(i) for i in range(1, len(pendientes) + 1)]
        op = pedir_opcion(opciones)
        if op == "0":
            return
        pantalla_detalle(pendientes[int(op) - 1])


def pantalla_detalle(lic: dict):
    """Muestra el detalle completo de una licitación y permite cambiar su estado."""
    while True:
        cabecera("Detalle de licitación")
        prio = lic.get("prioridad", "?")
        print(f"  Código    : {c(lic.get('codigo',''), 'azul')}")
        print(f"  Nombre    : {c(lic.get('nombre',''), 'negrita')}")
        print(f"  Organismo : {lic.get('organismo','')}")
        monto = lic.get("monto")
        print(f"  Monto     : {'${:,.0f}'.format(monto) if monto else 'N/D'}")
        dias = lic.get("dias_restantes")
        print(f"  Cierre    : {lic.get('fecha_cierre','')[:10]}  ({dias}d restantes)" if dias else f"  Cierre    : {lic.get('fecha_cierre','')[:10]}")
        print(f"  Prioridad : {c(prio.upper(), prio)}  (puntaje {lic.get('puntaje',0)}/10)")
        separador()
        print(f"  {c('Análisis IA:', 'azul')}")
        print(f"  {lic.get('justificacion','N/D')}")
        separador()
        print(f"  {c('Acciones recomendadas:', 'azul')}")
        print(f"  {lic.get('acciones','N/D')}")
        separador()
        print(f"  {c('Riesgos:', 'azul')}")
        print(f"  {lic.get('riesgos','N/D')}")
        separador()
        estado_actual = lic.get("estado", "nueva")
        print(f"  Estado actual: {c(estado_actual, ESTADO_COLOR.get(estado_actual,''))}")
        print()
        print(f"  {c('[o]', 'ok')}  Marcar para ofertar")
        print(f"  {c('[d]', 'alta')}  Descartar")
        print(f"  {c('[r]', 'azul')}  Marcar como revisada")
        print(f"  {c('[0]', 'azul')}  Volver")
        separador()

        op = pedir_opcion(["o", "d", "r", "0"])
        if op == "0":
            return
        estados = {"o": "ofertando", "d": "descartada", "r": "revisada"}
        nuevo_estado = estados[op]
        tracker.marcar_estado(lic["codigo"], nuevo_estado)
        lic["estado"] = nuevo_estado
        print(c(f"\n  ✓ Estado actualizado → {nuevo_estado}", "ok"))
        pausar()
        return


def pantalla_ofertando():
    """Lista las licitaciones marcadas para ofertar."""
    cabecera("Licitaciones a ofertar")
    lista = tracker.get_ofertando()

    if not lista:
        print(c("  No hay licitaciones marcadas para ofertar.", "azul"))
        pausar()
        return

    for lic in lista:
        dias = lic.get("dias_restantes")
        alerta = c(f" ⚠ {dias}d restantes", "alta") if dias is not None and dias < 10 else (f"  {dias}d" if dias else "")
        print(f"  {c(lic.get('codigo',''), 'azul'):20s}  {lic.get('nombre','')[:50]}{alerta}")
        print(f"    {lic.get('organismo','')[:50]}")
        print()
    pausar()


def pantalla_descargar():
    """Permite seleccionar una licitación y descargar sus bases."""
    pendientes = tracker.get_pendientes() + tracker.get_ofertando()
    cabecera(f"Descargar bases  ({len(pendientes)} licitaciones)")

    if not pendientes:
        print(c("  No hay licitaciones disponibles.", "azul"))
        pausar()
        return

    for i, lic in enumerate(pendientes, 1):
        carpeta = f"data/bases/{lic.get('codigo','')}"
        ya = "  (bases descargadas)" if os.path.isdir(carpeta) else ""
        print(f"  {c(str(i),'azul'):>4}.  {lic.get('nombre','')[:60]}{c(ya,'ok')}")

    separador()
    print("  Número de licitación  |  [0] Volver")
    opciones = ["0"] + [str(i) for i in range(1, len(pendientes) + 1)]
    op = pedir_opcion(opciones)
    if op == "0":
        return

    lic = pendientes[int(op) - 1]
    codigo = lic.get("codigo", "")
    print(f"\n  Obteniendo detalle de {c(codigo, 'azul')}...")

    if not API_KEY:
        print(c("  ✗ MP_API_KEY no configurada.", "alta"))
        pausar()
        return

    detalle = api.fetch_detalle(API_KEY, codigo)
    if not detalle:
        print(c("  ✗ No se pudo obtener el detalle.", "alta"))
        pausar()
        return

    print("  Descargando documentos...")
    archivos = downloader.descargar(codigo, detalle)
    print(c(f"\n  ✓ {len(archivos)} archivo(s) guardados en data/bases/{codigo}/", "ok"))
    for ruta in archivos:
        print(f"    · {os.path.basename(ruta)}")
    pausar()


def pantalla_historial():
    """Muestra el historial completo con colores por estado."""
    historial = tracker.get_historial()
    cabecera(f"Historial completo  ({len(historial)} licitaciones)")

    if not historial:
        print(c("  Aún no hay licitaciones registradas.", "azul"))
        pausar()
        return

    for lic in historial:
        estado = lic.get("estado", "nueva")
        col    = ESTADO_COLOR.get(estado, "")
        fecha  = lic.get("fecha_detectada", "")[:10]
        print(f"  {c(f'[{estado:10s}]', col)}  {lic.get('nombre','')[:55]}")
        print(f"              {lic.get('organismo','')[:45]}  |  detectada: {fecha}")
        print()
    pausar()


def pantalla_filtros():
    """Muestra la configuración activa de filtros."""
    cabecera("Filtros activos")
    separador()
    print(f"  Perfil de empresa  : {EMPRESA_DESC[:70]}")
    separador()
    print(f"  Rubros             : {', '.join(RUBROS) or '(todos)'}")
    print(f"  Keywords           : {', '.join(KEYWORDS) or '(ninguna)'}")
    print(f"  Reqs. técnicos     : {', '.join(REQS) or '(sin filtro)'}")
    separador()
    monto_min_txt = f"${MONTO_MIN:,.0f}" if MONTO_MIN else "sin límite"
    monto_max_txt = f"${MONTO_MAX:,.0f}" if MONTO_MAX else "sin límite"
    print(f"  Monto mínimo       : {monto_min_txt}")
    print(f"  Monto máximo       : {monto_max_txt}")
    print(f"  Días cierre mín.   : {DIAS_MIN if DIAS_MIN else 'sin límite'}")
    print(f"  Días cierre máx.   : {DIAS_MAX if DIAS_MAX else 'sin límite'}")
    separador()
    print(c("  Para cambiar filtros edita el archivo .env", "azul"))
    pausar()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tracker.init()

    while True:
        op = pantalla_menu_principal()
        if op == "0":
            limpiar()
            print(c("  Hasta luego.\n", "azul"))
            break
        elif op == "1":
            pantalla_buscar()
        elif op == "2":
            pantalla_pendientes()
        elif op == "3":
            pantalla_ofertando()
        elif op == "4":
            pantalla_descargar()
        elif op == "5":
            pantalla_historial()
        elif op == "6":
            pantalla_filtros()


if __name__ == "__main__":
    main()
