# Inna — Licitaciones Mercado Público Chile

Módulo independiente de revisión de licitaciones. Corre por separado de `main.py` con una interfaz interactiva de menús.

---

## Inicio rápido

```bash
cd asistente_virtual
python licitaciones.py
```

---

## Qué hace

1. **Busca** licitaciones activas en la API de Mercado Público (últimos 3 días)
2. **Omite** automáticamente las que ya fueron revisadas en sesiones anteriores
3. **Filtra** por tu perfil de empresa (rubros, keywords, monto, plazo, reqs. técnicos)
4. **Prioriza** con IA local (Ollama) → prioridad alta / media / baja + análisis
5. **Guarda** el historial en SQLite (`data/licitaciones.db`)
6. **Descarga** las bases de cada licitación para análisis posterior

---

## Menú interactivo

```
╔══════════════════════════════════════════════════════╗
║   INNA  ·  Licitaciones — Mercado Público Chile      ║
╚══════════════════════════════════════════════════════╝

  [1]  Buscar nuevas licitaciones
  [2]  Ver pendientes          (8 sin revisar)
  [3]  Licitaciones a ofertar  (2)
  [4]  Descargar bases
  [5]  Historial completo
  [6]  Filtros activos
  [0]  Salir
```

### Estados de una licitación

| Estado | Descripción |
|--------|-------------|
| `nueva` | Detectada, pendiente de revisión |
| `revisada` | Ya fue revisada, sin decisión |
| `ofertando` | Se decidió preparar oferta |
| `descartada` | Descartada manualmente |

Puedes cambiar el estado desde la pantalla de detalle de cada licitación.

---

## Configuración (`.env`)

Todas las opciones se editan en el archivo `.env`:

```env
# API Key de Mercado Público
MP_API_KEY=53CA2806-ED69-4108-9148-6F7B5C1A217F

# Rubros de interés (minúsculas, separados por coma)
MP_RUBROS=tecnologia,informatica,software,consultoria

# Palabras clave adicionales
MP_KEYWORDS=sistema,desarrollo,plataforma,soporte

# Descripción de tu empresa (usada por la IA para evaluar pertinencia)
MP_EMPRESA_DESC=Empresa proveedora de servicios tecnológicos...

# Capacidades y servicios
MP_CAPACIDADES=Desarrollo de software, consultoría TI...

# Filtro de monto en pesos CLP (0 = sin límite)
MP_MONTO_MIN=0
MP_MONTO_MAX=0

# Filtro de plazo en días (0 = sin límite)
MP_DIAS_CIERRE_MIN=3    # Descarta si cierra en menos de 3 días
MP_DIAS_CIERRE_MAX=90   # Descarta si cierra en más de 90 días

# Requerimientos técnicos obligatorios (vacío = sin filtro)
MP_REQS_TECNICOS=
```

---

## Estructura de archivos

```
asistente_virtual/
├── licitaciones.py                  ← Entry point (ejecutar esto)
├── .env                             ← Configuración y API Key
├── modules/
│   └── mercadopublico/
│       ├── api.py                   ← Cliente API Mercado Público
│       ├── filters.py               ← Filtros de perfil y dinámicos
│       ├── analyzer.py              ← Priorización con LLM (Ollama)
│       ├── downloader.py            ← Descarga de bases
│       └── tracker.py               ← Historial en SQLite
└── data/
    ├── licitaciones.db              ← Historial (auto-creado)
    └── bases/
        └── {CODIGO}/                ← Una carpeta por licitación
            ├── metadata.json        ← Datos completos de la licitación
            └── *.pdf / *.docx       ← Documentos descargados
```

---

## Requisitos

- Python 3.11+
- Ollama corriendo localmente (`ollama serve`) — requerido solo para la priorización con IA
- Las mismas dependencias de `requirements.txt`

Sin Ollama la búsqueda y los filtros funcionan igual, pero sin el análisis de prioridad.

---

## Solución de problemas

**Error 401 al conectar**
```
Verifica que MP_API_KEY en .env sea correcta.
```

**"Ninguna licitación coincide con tu perfil"**
```
Revisa MP_RUBROS y MP_KEYWORDS en .env.
Usa [6] Filtros activos para ver la configuración actual.
```

**No se descargan los documentos**
```
Algunas licitaciones no tienen adjuntos en la API.
Se guarda un archivo ver_en_portal.txt con el link directo.
```

**Sin priorización IA**
```
Inicia Ollama: ollama serve
Descarga un modelo si no tienes: ollama pull mistral
```
