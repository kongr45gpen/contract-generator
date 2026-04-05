from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, FloatObject, NameObject, NullObject, NumberObject, TextStringObject

from contract_generator.schema import ModelReleaseContract
from contract_generator.templates.model_release import FIELD_SPECS, render_model_release_body


PAGE_WIDTH, PAGE_HEIGHT = letter

INK = HexColor("#111827")
MUTED = HexColor("#475569")
LINE = HexColor("#CBD5E1")
PAPER = HexColor("#F8FAFC")
ACCENT = HexColor("#0F766E")
ACCENT_LIGHT = HexColor("#CCFBF1")
WHITE = HexColor("#FFFFFF")


def _format_display_value(value: object) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    return str(value)


def _draw_field(canvas: Canvas, x: float, y: float, width: float, label: str, value: str, key: str) -> None:
    label_style = ParagraphStyle(
        name=f"label_{key}",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=MUTED,
        alignment=TA_LEFT,
    )
    label_box = Paragraph(label.upper(), label_style)
    label_box.wrapOn(canvas, width, 12)
    label_box.drawOn(canvas, x, y + 19)

    canvas.acroForm.textfield(
        name=key,
        tooltip=label,
        x=x,
        y=y,
        width=width,
        height=18,
        borderWidth=1,
        borderStyle="underlined",
        borderColor=LINE,
        fillColor=WHITE,
        textColor=INK,
        forceBorder=True,
        value=value,
    )


def _draw_header(canvas: Canvas, contract: ModelReleaseContract) -> None:
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    canvas.setFillColor(INK)
    canvas.roundRect(30, PAGE_HEIGHT - 124, PAGE_WIDTH - 60, 94, 18, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.roundRect(30, PAGE_HEIGHT - 124, 12, 94, 6, fill=1, stroke=0)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawString(56, PAGE_HEIGHT - 66, contract.document_title)
    canvas.setFont("Helvetica", 9.5)
    canvas.setFillColor(ACCENT_LIGHT)
    canvas.drawString(56, PAGE_HEIGHT - 84, f"Programmatically generated contract template for {contract.project_name}")

    pill_x = PAGE_WIDTH - 220
    pill_y = PAGE_HEIGHT - 92
    canvas.setFillColor(ACCENT_LIGHT)
    canvas.roundRect(pill_x, pill_y, 162, 28, 14, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(pill_x + 81, pill_y + 9, contract.effective_date.isoformat())

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(56, PAGE_HEIGHT - 102, f"Project: {contract.project_name}")
    canvas.drawString(220, PAGE_HEIGHT - 102, f"Location: {contract.location}")
    canvas.restoreState()


def _draw_section_card(canvas: Canvas, x: float, y: float, width: float, height: float, title: str, subtitle: str | None = None) -> None:
    canvas.saveState()
    canvas.setFillColor(WHITE)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(x, y, width, height, 16, fill=1, stroke=1)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(x + 18, y + height - 24, title)
    if subtitle:
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(x + 18, y + height - 37, subtitle)
    canvas.restoreState()


def _draw_fields(canvas: Canvas, contract: ModelReleaseContract) -> None:
    x = 42
    y = 500
    card_width = PAGE_WIDTH - 84
    card_height = 180
    _draw_section_card(canvas, x, y, card_width, card_height, "Editable Details", "These form fields remain editable in standard PDF viewers.")

    left_x = x + 18
    right_x = x + card_width / 2 + 8
    field_width = card_width / 2 - 26
    row_gap = 32
    top = y + card_height - 62

    values = {spec.key: _format_display_value(getattr(contract, spec.key)) for spec in FIELD_SPECS}
    spec_index = 0
    current_y = top
    while spec_index < len(FIELD_SPECS):
        spec = FIELD_SPECS[spec_index]
        if spec.span == 2:
            _draw_field(canvas, left_x, current_y, card_width - 36, spec.label, values[spec.key], spec.key)
            current_y -= row_gap
            spec_index += 1
            continue

        next_spec = FIELD_SPECS[spec_index + 1] if spec_index + 1 < len(FIELD_SPECS) else None
        if next_spec and next_spec.span == 1:
            _draw_field(canvas, left_x, current_y, field_width, spec.label, values[spec.key], spec.key)
            _draw_field(canvas, right_x, current_y, field_width, next_spec.label, values[next_spec.key], next_spec.key)
            current_y -= row_gap
            spec_index += 2
        else:
            _draw_field(canvas, left_x, current_y, card_width - 36, spec.label, values[spec.key], spec.key)
            current_y -= row_gap
            spec_index += 1


def _draw_body(canvas: Canvas, contract: ModelReleaseContract) -> None:
    x = 42
    y = 255
    width = PAGE_WIDTH - 84
    height = 230
    _draw_section_card(canvas, x, y, width, height, "Agreement Summary", "The text below is generated from the same contract parameters.")

    body_style = ParagraphStyle(
        name="contract_body",
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=INK,
    )
    body = Paragraph(render_model_release_body(contract), body_style)
    body_width = width - 36
    body_height = height - 54
    body.wrapOn(canvas, body_width, body_height)
    body.drawOn(canvas, x + 18, y + 18)


def _draw_signature_section(canvas: Canvas) -> None:
    x = 42
    y = 78
    width = PAGE_WIDTH - 84
    height = 150
    _draw_section_card(canvas, x, y, width, height, "Signature", "The field below is a real PDF signature widget.")

    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(x + 18, y + 86, "Sign below to accept the release.")
    canvas.setStrokeColor(LINE)
    canvas.line(x + 18, y + 45, x + width - 18, y + 45)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(x + 18, y + 32, "SIGNATURE")


def _inject_signature_field(pdf_bytes: bytes) -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    page = writer.pages[-1]
    signature_rect = ArrayObject([FloatObject(60), FloatObject(132), FloatObject(320), FloatObject(156)])
    signature_field = DictionaryObject(
        {
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/T"): TextStringObject("subject_signature"),
            NameObject("/TU"): TextStringObject("Signature"),
            NameObject("/F"): NumberObject(4),
            NameObject("/Ff"): NumberObject(0),
            NameObject("/Rect"): signature_rect,
            NameObject("/V"): NullObject(),
            NameObject("/P"): page.indirect_reference,
        }
    )
    signature_ref = writer._add_object(signature_field)

    annotations = page.get("/Annots")
    if annotations is None:
        annotations = ArrayObject()
        page[NameObject("/Annots")] = annotations
    elif hasattr(annotations, "get_object"):
        annotations = annotations.get_object()
    annotations.append(signature_ref)

    acroform = writer._root_object.get("/AcroForm")
    if acroform is None:
        acroform = DictionaryObject()
        writer._root_object[NameObject("/AcroForm")] = acroform
    elif hasattr(acroform, "get_object"):
        acroform = acroform.get_object()

    fields = acroform.get("/Fields")
    if fields is None:
        fields = ArrayObject()
        acroform[NameObject("/Fields")] = fields
    elif hasattr(fields, "get_object"):
        fields = fields.get_object()
    fields.append(signature_ref)

    acroform[NameObject("/NeedAppearances")] = BooleanObject(True)
    acroform[NameObject("/SigFlags")] = NumberObject(3)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def generate_contract_pdf(contract: ModelReleaseContract, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=letter)
    canvas.setAuthor("Contract Generator")
    canvas.setTitle(contract.document_title)
    canvas.setSubject("Generated contract PDF")
    canvas.setCreator("contract-generator")
    canvas.setFont("Helvetica", 10)

    _draw_header(canvas, contract)
    _draw_fields(canvas, contract)
    _draw_body(canvas, contract)
    _draw_signature_section(canvas)

    canvas.showPage()
    canvas.save()

    output.write_bytes(_inject_signature_field(buffer.getvalue()))
    return output
