import os
import textwrap
import uuid
from datetime import date
from urllib.parse import quote

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

# A4: 595 x 842 pt; ruime marge, één pagina
_MARGIN_X = 56
_MARGIN_BOTTOM = 56
# Inhoud stopt boven de disclaimer (vast blok onderaan)
_CONTENT_FLOOR = 118
_FOOT_BASE = 64
_LINE = 14
_LINE_TIGHT = 12
_MAX_CHARS = 82
# Voorkom PDF-bom
_MAX_NAME = 300
_MAX_FIELD = 2500
_MAX_POINT = 400
_MAX_POINTS = 8


def _type_title(type_):
    if type_ == "offerte":
        return "Offerte (PDS)"
    if type_ == "technisch":
        return "Technische PDS"
    if type_ == "commercieel":
        return "Commerciële PDS"
    return "PDS"


def _wrap_lines(text, width=_MAX_CHARS):
    if not (text or "").strip():
        return []
    out = []
    for para in str(text).splitlines():
        p = para.strip()
        if not p:
            out.append("")
        else:
            out.extend(textwrap.wrap(p, width=width) or [""])
    return out


def _draw_lines(pdf, lines, x, y, line_height, floor=_CONTENT_FLOOR):
    for line in lines:
        if y < floor + line_height * 2:
            break
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def _section(pdf, label, x, y, value, line_height=_LINE, wrap_height=_LINE_TIGHT):
    if not (value or "").strip():
        return y
    if y < _CONTENT_FLOOR + 80:
        return y
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, label)
    y -= line_height
    pdf.setFont("Helvetica", 10)
    for part in _wrap_lines(value):
        if y < _CONTENT_FLOOR:
            return y
        pdf.drawString(x, y, part)
        y -= wrap_height
    y -= 4
    return y


def generate_pds(data, output_dir):
    name = str(data.get("name", "")).strip()[:_MAX_NAME]
    if not name:
        raise ValueError("Missing name")
    type_ = str(data.get("type", "offerte")).strip().lower()

    goal = str(data.get("goal", "")).strip()[:_MAX_FIELD]
    summary = str(data.get("summary", "")).strip()[:_MAX_FIELD]
    document_date = str(data.get("document_date", "")).strip()[:50]
    if not document_date:
        document_date = date.today().strftime("%d-%m-%Y")
    client = str(data.get("client", "")).strip()[:_MAX_FIELD]
    points = data.get("points")
    if not isinstance(points, list):
        points = []
    points = [
        str(p).strip()[:_MAX_POINT] for p in points if str(p).strip()
    ][: _MAX_POINTS]

    raw = name[:-4] if name.lower().endswith(".pdf") else name
    safe_base = (secure_filename(raw) or "unknown")[:100]
    unique_id = uuid.uuid4().hex[:8]
    safe_name = f"{safe_base}_{unique_id}.pdf"

    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, safe_name)

    pdf = canvas.Canvas(file_path, pagesize=A4)
    pdf.setTitle(f"{_type_title(type_)} — {name}")
    y = 800
    x = _MARGIN_X

    pdf.setFont("Helvetica-Bold", 18)
    title = _type_title(type_)
    for line in _wrap_lines(title, width=40):
        pdf.drawString(x, y, line)
        y -= 22
    y -= 8

    pdf.setFont("Helvetica", 9)
    pdf.setFillGray(0.35)
    pdf.drawString(x, y, f"Documentdatum: {document_date}")
    y -= _LINE
    pdf.setFillGray(0)
    y -= 6

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x, y, "Project")
    y -= _LINE
    pdf.setFont("Helvetica", 11)
    y = _draw_lines(pdf, _wrap_lines(name) or [name], x, y, _LINE_TIGHT)
    y -= 8

    if client:
        y = _section(pdf, "Opdrachtgever / relatie", x, y, client)

    y = _section(pdf, "Doel van dit document", x, y, goal)

    if points and y >= _CONTENT_FLOOR + 60:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x, y, "Kernpunten")
        y -= _LINE
        pdf.setFont("Helvetica", 10)
        for p in points:
            if y < _CONTENT_FLOOR:
                break
            for part in _wrap_lines(f"• {p}"):
                if y < _CONTENT_FLOOR:
                    break
                pdf.drawString(x, y, part)
                y -= _LINE_TIGHT
        y -= 4

    y = _section(pdf, "Samenvatting", x, y, summary)

    # Vast onderaan, geen overlap met lange bovenkant: inhoud eindigt boven _CONTENT_FLOOR
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.setFillGray(0.45)
    foot = (
        "Werkdocument — vul aan waar nodig; controleer aansluiting op offerte, "
        "meting en leveringsvoorwaarden voordat je dit deelt."
    )
    y_foot = _FOOT_BASE
    for part in _wrap_lines(foot, width=90):
        if y_foot < _MARGIN_BOTTOM + 2:
            break
        pdf.drawString(x, y_foot, part)
        y_foot -= 10
    pdf.setFillGray(0)
    pdf.save()

    encoded_name = quote(safe_name)
    return {
        "name": name,
        "type": type_,
        "filename": safe_name,
        "download_url": f"/pds/download/{encoded_name}",
    }
