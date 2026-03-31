"""
Generador de reportes diarios en PDF y HTML.
Consolida: correos clasificados, respuestas sugeridas y agenda del calendario.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from modules.llm_engine import ask_llm
from modules.email_reader import DB_PATH

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ─────────────────────────────────────────────
#  RESUMEN EJECUTIVO VIA LLM
# ─────────────────────────────────────────────

def generate_executive_summary(emails: list[dict]) -> str:
    """Genera un resumen ejecutivo del día usando el LLM."""
    if not emails:
        return "No se recibieron correos nuevos en este periodo."

    combined = "\n".join([
        f"- [{e['category'].upper()}] De: {e['sender']} | Asunto: {e['subject']}"
        for e in emails
    ])

    prompt = f"""Analiza estos correos del dia y genera un resumen ejecutivo breve (6-8 lineas):
{combined}

El resumen debe indicar:
1. Cuantos correos urgentes/importantes hay
2. Los temas principales
3. Acciones recomendadas"""

    system = "Eres un asistente ejecutivo. Redacta resumenes claros y orientados a la accion."
    return ask_llm(prompt, system=system)


# ─────────────────────────────────────────────
#  REPORTE HTML (siempre disponible)
# ─────────────────────────────────────────────

def build_html_report(emails: list[dict], events: list[dict],
                       conflicts: list[str], summary: str,
                       replies: list[dict]) -> str:
    """Genera el reporte completo en formato HTML."""

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    category_colors = {
        "urgente":     "#dc3545",
        "importante":  "#fd7e14",
        "informativo": "#0d6efd",
        "spam":        "#6c757d",
    }

    def badge(cat):
        color = category_colors.get(cat, "#999")
        return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold">{cat.upper()}</span>'

    # Tabla de correos
    email_rows = ""
    for e in emails:
        email_rows += f"""
        <tr>
            <td>{badge(e.get('category','?'))}</td>
            <td><b>{e['subject']}</b></td>
            <td>{e['sender']}</td>
            <td style="font-size:12px;color:#666">{e['date'][:16]}</td>
        </tr>"""

    # Respuestas sugeridas
    reply_blocks = ""
    for r in replies:
        reply_blocks += f"""
        <div style="border-left:4px solid #0d6efd;padding:10px 16px;margin:10px 0;background:#f8f9ff">
            <b>Re: {r['subject']}</b><br>
            <span style="color:#555">Para: {r.get('sender','')}</span><br><br>
            <p style="white-space:pre-wrap">{r['reply']}</p>
        </div>"""

    # Agenda
    event_rows = ""
    for ev in events:
        event_rows += f"""
        <tr>
            <td><b>{ev['start']}</b></td>
            <td>{ev['summary']}</td>
            <td style="color:#666">{ev.get('location','')}</td>
        </tr>"""

    # Conflictos
    conflict_html = ""
    if conflicts:
        conflict_items = "".join(f"<li>{c}</li>" for c in conflicts)
        conflict_html = f"""
        <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:12px;margin:10px 0">
            <b>Conflictos detectados:</b>
            <ul>{conflict_items}</ul>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Informe Diario — {now}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #0d6efd; padding-bottom: 8px; }}
        h2 {{ color: #1a1a2e; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th {{ background: #1a1a2e; color: white; padding: 8px 12px; text-align: left; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
        tr:hover td {{ background: #f5f5f5; }}
        .summary-box {{ background: #e8f4fd; border-radius: 8px; padding: 16px; margin: 10px 0; }}
        .footer {{ text-align: center; color: #999; margin-top: 40px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Informe Diario — Inna</h1>
    <p style="color:#666">Generado el {now}</p>

    <h2>Resumen Ejecutivo</h2>
    <div class="summary-box">
        <p style="white-space:pre-wrap">{summary}</p>
    </div>

    <h2>Correos Clasificados ({len(emails)} total)</h2>
    <table>
        <tr><th>Categoria</th><th>Asunto</th><th>Remitente</th><th>Fecha</th></tr>
        {email_rows if email_rows else '<tr><td colspan="4" style="text-align:center;color:#999">Sin correos nuevos</td></tr>'}
    </table>

    {'<h2>Respuestas Sugeridas</h2>' + reply_blocks if reply_blocks else ''}

    <h2>Agenda — Proximos 7 dias</h2>
    {conflict_html}
    <table>
        <tr><th>Fecha/Hora</th><th>Evento</th><th>Lugar</th></tr>
        {event_rows if event_rows else '<tr><td colspan="3" style="text-align:center;color:#999">Sin eventos programados</td></tr>'}
    </table>

    <div class="footer">Inna — Asistente Virtual Local — {now}</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────
#  REPORTE PDF (requiere reportlab)
# ─────────────────────────────────────────────

def build_pdf_report(emails, events, conflicts, summary, replies, output_path):
    """Genera el reporte en PDF usando ReportLab."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("Instala reportlab: pip install reportlab")

    doc    = SimpleDocTemplate(str(output_path), pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    def h1(text):
        story.append(Paragraph(text, styles["Title"]))
        story.append(Spacer(1, 10))

    def h2(text):
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>{text}</b>", styles["Heading2"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0d6efd")))
        story.append(Spacer(1, 6))

    def p(text):
        story.append(Paragraph(text.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 4))

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    h1(f"Informe Diario — {now}")

    h2("Resumen Ejecutivo")
    p(summary)

    h2(f"Correos Clasificados ({len(emails)} total)")
    if emails:
        data = [["Categoria", "Asunto", "Remitente"]]
        for e in emails:
            data.append([
                e.get("category", "?").upper(),
                e["subject"][:45],
                e["sender"][:35]
            ])
        t = Table(data, colWidths=[3*cm, 9*cm, 6*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("PADDING",    (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    if replies:
        h2("Respuestas Sugeridas")
        for r in replies:
            p(f"<b>Re: {r['subject']}</b>")
            p(r["reply"])
            story.append(Spacer(1, 6))

    h2("Agenda — Proximos 7 dias")
    if conflicts:
        for c in conflicts:
            p(f"<font color='red'>⚠ {c}</font>")
    if events:
        data = [["Fecha/Hora", "Evento", "Lugar"]]
        for ev in events:
            data.append([ev["start"], ev["summary"][:40], ev.get("location", "")[:25]])
        t = Table(data, colWidths=[4*cm, 10*cm, 4*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("PADDING",    (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        p("Sin eventos programados.")

    doc.build(story)


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def build_report(events: list[dict], conflicts: list[str]) -> dict:
    """
    Construye el reporte completo (HTML + PDF si está disponible).

    Returns:
        Dict con las rutas de los archivos generados.
    """
    Path("data/reports").mkdir(parents=True, exist_ok=True)

    # Cargar datos desde BD
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, subject, sender, date, body, category, reply FROM emails WHERE processed=0"
    ).fetchall()
    conn.close()

    emails = [
        {"id": r[0], "subject": r[1], "sender": r[2],
         "date": r[3], "body": r[4], "category": r[5], "reply": r[6]}
        for r in rows
    ]

    # Respuestas para correos urgentes/importantes
    replies = [
        {"subject": e["subject"], "sender": e["sender"], "reply": e["reply"]}
        for e in emails if e["reply"] and e["category"] in ("urgente", "importante")
    ]

    # Generar resumen ejecutivo
    print("  Generando resumen ejecutivo con LLM...")
    summary = generate_executive_summary(emails)

    # Timestamp para nombres de archivo
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    output_files = {}

    # HTML (siempre)
    html_path = Path(f"data/reports/reporte_{ts}.html")
    html_content = build_html_report(emails, events, conflicts, summary, replies)
    html_path.write_text(html_content, encoding="utf-8")
    output_files["html"] = str(html_path)
    print(f"  Reporte HTML: {html_path}")

    # PDF (si reportlab está instalado)
    if REPORTLAB_AVAILABLE:
        pdf_path = Path(f"data/reports/reporte_{ts}.pdf")
        build_pdf_report(emails, events, conflicts, summary, replies, pdf_path)
        output_files["pdf"] = str(pdf_path)
        print(f"  Reporte PDF:  {pdf_path}")
    else:
        print("  [INFO] reportlab no instalado — solo se genera HTML.")

    return output_files
