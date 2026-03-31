# Inna — Asistente Virtual Local

Sistema de automatización inteligente que corre completamente en tu equipo (on-premise), sin depender de servicios pagos. Analiza correos, gestiona tu agenda y genera reportes diarios usando modelos de IA locales.

---

## Características

- **Lectura de correos** vía IMAP — compatible con Gmail, Outlook y cualquier proveedor estándar
- **Clasificación automática** con IA local: urgente, importante, informativo, spam
- **Respuestas sugeridas** redactadas por el modelo de lenguaje
- **Lectura de calendario** desde archivos `.ics` (Google Calendar, Outlook, Apple Calendar)
- **Detección de conflictos** de horario
- **Reporte diario consolidado** en HTML y PDF
- **Envío automático** del reporte por correo
- **Scheduler integrado** con ejecución en horarios configurables
- **100% local y gratuito** — usa Ollama como motor de IA

---

## Requisitos

| Herramienta | Versión mínima |
|-------------|---------------|
| Python      | 3.11+         |
| Ollama      | Última        |
| Windows     | 10 / 11       |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/fgodoy93/asistente_virtual.git
cd asistente_virtual
```

### 2. Instalar Ollama

Descarga e instala desde [ollama.com/download/windows](https://ollama.com/download/windows), luego descarga un modelo:

```bash
ollama pull mistral
```

> Modelos recomendados según tu hardware:
> | Modelo | RAM requerida | Calidad |
> |--------|--------------|---------|
> | `phi3:mini` | 2 GB | Media |
> | `mistral:7b` | 4 GB | Alta |
> | `llama3:8b` | 5 GB | Muy alta |

### 3. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

Copia el archivo de ejemplo y completa tus datos:

```bash
cp .env.example .env
```

Edita `.env`:

```env
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USER=tu_correo@gmail.com
EMAIL_PASS=tu_app_password

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=mistral

ICS_PATH=data/calendar.ics
REPORT_EMAIL=tu_correo@gmail.com
```

> **Gmail:** Debes usar una *App Password*, no tu contraseña normal.
> Generala en: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 5. Agregar tu calendario (opcional)

Exporta tu calendario desde Google Calendar:
`Configuración → Importar y exportar → Exportar`

Copia el archivo `.ics` descargado a `data/calendar.ics`.

---

## Uso

### Verificar que todo está configurado

```bash
python main.py --check
```

### Ejecutar el asistente

```bash
# Ejecución completa con envío de reporte por correo
python main.py

# Sin enviar el reporte por correo
python main.py --no-email
```

### Automatizar con el scheduler

```bash
# Inicia el scheduler (07:00, 13:00 y 18:00)
python scheduler.py

# Ejecutar ahora + activar scheduler
python scheduler.py --now
```

### Registrar en Windows Task Scheduler (ejecución automática al iniciar Windows)

Ejecuta esto en PowerShell como Administrador:

```powershell
schtasks /create /tn "AsistenteVirtual" `
  /tr "python C:\ruta\al\proyecto\scheduler.py --now" `
  /sc daily /st 07:00
```

---

## Estructura del proyecto

```
asistente_virtual/
├── .env.example              # Plantilla de configuración
├── .gitignore
├── config.py                 # Carga variables de entorno
├── main.py                   # Orquestador principal
├── scheduler.py              # Automatización por horarios
├── requirements.txt
└── modules/
    ├── llm_engine.py         # Abstracción sobre Ollama
    ├── email_reader.py       # Conexión IMAP + SQLite
    ├── email_classifier.py   # Clasificación con LLM
    ├── email_responder.py    # Respuestas sugeridas + SMTP
    ├── calendar_reader.py    # Lectura .ics + conflictos
    └── report_generator.py  # Generación HTML + PDF
```

Los reportes se guardan en `data/reports/` con timestamp.

---

## Pipeline de ejecución

```
Correos IMAP
     ↓
  SQLite DB  ──→  Clasificación LLM  ──→  Respuestas LLM
                                                 ↓
Calendario .ics ──────────────────────→  Reporte HTML/PDF
                                                 ↓
                                        Envío por correo
```

---

## Tecnologías utilizadas

| Componente | Tecnología |
|-----------|-----------|
| LLM local | [Ollama](https://ollama.com) + Mistral / LLaMA 3 |
| Correos | `imaplib` / `smtplib` (Python stdlib) |
| Calendario | `icalendar` |
| Base de datos | SQLite (`sqlite3` stdlib) |
| PDF | `reportlab` |
| Scheduler | `schedule` |
| Configuración | `python-dotenv` |

---

## Solución de problemas

**Ollama no disponible**
```
Asegúrate de que Ollama esté corriendo: ollama serve
```

**Error de autenticación IMAP (Gmail)**
```
Gmail requiere una App Password. No uses tu contraseña normal.
Actívala en: myaccount.google.com/apppasswords
```

**No se genera PDF**
```
pip install reportlab
```

**El modelo tarda mucho**
```
Prueba con un modelo más liviano: ollama pull phi3:mini
Luego actualiza OLLAMA_MODEL=phi3:mini en tu .env
```

---

## Licencia

MIT — libre para uso personal y comercial.
