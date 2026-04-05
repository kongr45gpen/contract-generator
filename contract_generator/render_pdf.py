from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from markdown_it import MarkdownIt
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, FloatObject, NameObject, NullObject, NumberObject, TextStringObject

from contract_generator.schema import ContractRequest
from contract_generator.template_registry import get_template_definition, validate_template_parameters
from contract_generator.template_support.types import Clause, InlineField
from contract_generator.template_support.utils import defaults_for_fields, labels_for_fields, widths_for_fields


PAGE_WIDTH, PAGE_HEIGHT = letter

INK = HexColor("#0F172A")
MUTED = HexColor("#475569")
LINE = HexColor("#D1D5DB")
ACCENT = HexColor("#0D9488")
WHITE = HexColor("#FFFFFF")

LEFT_MARGIN = 56
RIGHT_MARGIN = 56
TOP_MARGIN = 128
BOTTOM_MARGIN = 64
MARKDOWN_PARSER = MarkdownIt("commonmark")


@dataclass(frozen=True)
class _FieldPlacement:
    key: str
    label: str
    x: float
    y: float
    width: float
    height: float
    value: str


@dataclass(frozen=True)
class _InlineRun:
    text: str
    is_code: bool


@dataclass(frozen=True)
class _MarkdownBlock:
    kind: str
    level: int
    runs: list[_InlineRun]


def _register_fonts() -> tuple[str, str]:
    regular = Path("/usr/share/fonts/TTF/DejaVuSans.ttf")
    bold = Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf")

    if regular.exists() and bold.exists():
        if "ModernSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ModernSans", str(regular)))
        if "ModernSans-Bold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ModernSans-Bold", str(bold)))
        return "ModernSans", "ModernSans-Bold"

    return "Helvetica", "Helvetica-Bold"


def _inline_runs_from_markdown_token(token: object) -> list[_InlineRun]:
    runs: list[_InlineRun] = []
    children = getattr(token, "children", None) or []
    for child in children:
        child_type = getattr(child, "type", "")
        content = getattr(child, "content", "")
        if child_type == "text" and content:
            runs.append(_InlineRun(text=content, is_code=False))
        elif child_type == "code_inline":
            runs.append(_InlineRun(text=content, is_code=True))
        elif child_type in {"softbreak", "hardbreak"}:
            runs.append(_InlineRun(text="\n", is_code=False))
    return runs


def _parse_markdown_blocks(markdown: str) -> list[_MarkdownBlock]:
    tokens = MARKDOWN_PARSER.parse(markdown)
    blocks: list[_MarkdownBlock] = []
    list_stack: list[tuple[str, int]] = []
    pending_list_prefix: str | None = None

    index = 0
    while index < len(tokens):
        token = tokens[index]
        token_type = getattr(token, "type", "")

        if token_type == "bullet_list_open":
            list_stack.append(("bullet", 1))
            index += 1
            continue

        if token_type == "ordered_list_open":
            start = int(getattr(token, "attrs", {}).get("start", 1)) if isinstance(getattr(token, "attrs", None), dict) else 1
            list_stack.append(("ordered", start))
            index += 1
            continue

        if token_type in {"bullet_list_close", "ordered_list_close"}:
            if list_stack:
                list_stack.pop()
            index += 1
            continue

        if token_type == "list_item_open":
            if list_stack:
                kind, counter = list_stack[-1]
                if kind == "ordered":
                    pending_list_prefix = f"{counter}. "
                    list_stack[-1] = (kind, counter + 1)
                else:
                    pending_list_prefix = "- "
            else:
                pending_list_prefix = "- "
            index += 1
            continue

        if token_type == "heading_open":
            level = int(getattr(token, "tag", "h1")[1:])
            inline_token = tokens[index + 1] if index + 1 < len(tokens) else None
            if inline_token is not None and getattr(inline_token, "type", "") == "inline":
                runs = _inline_runs_from_markdown_token(inline_token)
                if runs:
                    blocks.append(_MarkdownBlock(kind="heading", level=level, runs=runs))
            index += 1
            continue

        if token_type == "inline":
            runs = _inline_runs_from_markdown_token(token)
            if runs:
                if pending_list_prefix:
                    runs.insert(0, _InlineRun(text=pending_list_prefix, is_code=False))
                    pending_list_prefix = None
                blocks.append(_MarkdownBlock(kind="paragraph", level=0, runs=runs))

        index += 1

    return blocks


def _draw_inline_runs(
    canvas: Canvas,
    runs: list[_InlineRun],
    *,
    x: float,
    y: float,
    max_width: float,
    normal_font: str,
    text_size: float,
    line_height: float,
) -> float:
    cursor_x = x

    for run in runs:
        if run.text == "\n":
            y -= line_height
            cursor_x = x
            continue
        chunks = re.findall(r"\S+\s*", run.text)
        for chunk in chunks:
            if run.is_code:
                text_width = pdfmetrics.stringWidth(chunk.rstrip(), "Courier", text_size)
                box_width = text_width + 6
                if cursor_x > x and cursor_x + box_width > x + max_width:
                    y -= line_height
                    cursor_x = x
                canvas.setFillColor(HexColor("#EAEAEA"))
                canvas.roundRect(cursor_x, y - 2, box_width, 9, 2, fill=1, stroke=0)
                canvas.setFillColor(HexColor("#111111"))
                canvas.setFont("Courier", text_size)
                canvas.drawString(cursor_x + 3, y, chunk.rstrip())
                cursor_x += box_width
                continue

            text_width = pdfmetrics.stringWidth(chunk, normal_font, text_size)
            if cursor_x > x and cursor_x + text_width > x + max_width:
                y -= line_height
                cursor_x = x
            canvas.setFillColor(MUTED)
            canvas.setFont(normal_font, text_size)
            canvas.drawString(cursor_x, y, chunk)
            cursor_x += text_width

    return y - line_height


def _draw_generic_header(canvas: Canvas, header_markdown: str | None, normal_font: str) -> float:
    if not header_markdown:
        return PAGE_HEIGHT - TOP_MARGIN

    header_y = PAGE_HEIGHT - 24
    max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    cursor_y = header_y

    for block in _parse_markdown_blocks(header_markdown):
        if block.kind == "heading":
            heading_size = max(8.5, 11 - block.level)
            cursor_y = _draw_inline_runs(
                canvas,
                block.runs,
                x=LEFT_MARGIN,
                y=cursor_y,
                max_width=max_width,
                normal_font=normal_font,
                text_size=heading_size,
                line_height=heading_size + 3,
            )
            continue
        cursor_y = _draw_inline_runs(
            canvas,
            block.runs,
            x=LEFT_MARGIN,
            y=cursor_y,
            max_width=max_width,
            normal_font=normal_font,
            text_size=8,
            line_height=11,
        )

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    separator_y = cursor_y + 3
    canvas.line(LEFT_MARGIN, separator_y, PAGE_WIDTH - RIGHT_MARGIN, separator_y)
    return separator_y - 32


def _draw_generic_footer(canvas: Canvas, footer_markdown: str | None, normal_font: str) -> None:
    if not footer_markdown:
        return

    max_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    cursor_y = 24

    for block in _parse_markdown_blocks(footer_markdown):
        cursor_y = _draw_inline_runs(
            canvas,
            block.runs,
            x=LEFT_MARGIN,
            y=cursor_y,
            max_width=max_width,
            normal_font=normal_font,
            text_size=7.5,
            line_height=10,
        )


def _draw_header(canvas: Canvas, contract: object, normal_font: str, bold_font: str, top_y: float) -> float:
    canvas.setFillColor(INK)
    canvas.setFont(bold_font, 22)
    canvas.drawString(LEFT_MARGIN, top_y, str(getattr(contract, "document_title")))

    canvas.setFillColor(MUTED)
    canvas.setFont(normal_font, 10)
    canvas.drawString(
        LEFT_MARGIN,
        top_y - 18,
        f"Project: {getattr(contract, 'project_name')}   |   Effective Date: {getattr(contract, 'effective_date').isoformat()}",
    )

    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.6)
    canvas.line(LEFT_MARGIN, top_y - 27, PAGE_WIDTH - RIGHT_MARGIN, top_y - 27)
    return top_y - 48


def _draw_wrapped_text(canvas: Canvas, text: str, x: float, y: float, width: float, line_height: float, font_name: str, font_size: float) -> float:
    canvas.setFont(font_name, font_size)
    right = x + width
    space_width = pdfmetrics.stringWidth(" ", font_name, font_size)
    cursor_x = x
    cursor_y = y
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            cursor_y -= line_height
            cursor_x = x
            continue
        for word in words:
            word_width = pdfmetrics.stringWidth(word, font_name, font_size)
            if cursor_x > x and cursor_x + word_width > right:
                cursor_y -= line_height
                cursor_x = x
            canvas.drawString(cursor_x, cursor_y, word)
            cursor_x += word_width + space_width
        cursor_y -= line_height
        cursor_x = x
    return cursor_y


def _draw_text_segment(
    canvas: Canvas,
    segment: str,
    *,
    x_start: float,
    x_right: float,
    cursor_x: float,
    cursor_y: float,
    font_name: str,
    font_size: float,
    line_height: float,
) -> tuple[float, float]:
    tokens = re.findall(r"\S+\s*", segment)
    for token in tokens:
        token_width = pdfmetrics.stringWidth(token, font_name, font_size)
        if cursor_x > x_start and cursor_x + token_width > x_right:
            cursor_y -= line_height
            cursor_x = x_start
        canvas.drawString(cursor_x, cursor_y, token)
        cursor_x += token_width
    return cursor_x, cursor_y


def _draw_inline_clause(
    canvas: Canvas,
    clause: Clause,
    field_defaults: dict[str, str],
    field_labels: dict[str, str],
    field_widths: dict[str, float],
    *,
    x_start: float,
    x_right: float,
    start_y: float,
    normal_font: str,
    bold_font: str,
) -> tuple[float, list[_FieldPlacement]]:
    title_font_size = 9
    body_font_size = 10.5
    line_height = 16
    heading_gap = 16
    clause_gap = 16
    field_height = 10.5

    placements: list[_FieldPlacement] = []

    if clause.heading:
        canvas.setFillColor(INK)
        canvas.setFont(bold_font, title_font_size)
        canvas.drawString(x_start, start_y, f"{clause.heading}.")

    cursor_x = x_start
    cursor_y = start_y - heading_gap
    canvas.setFont(normal_font, body_font_size)

    for segment in clause.segments:
        if isinstance(segment, str):
            cursor_x, cursor_y = _draw_text_segment(
                canvas,
                segment,
                x_start=x_start,
                x_right=x_right,
                cursor_x=cursor_x,
                cursor_y=cursor_y,
                font_name=normal_font,
                font_size=body_font_size,
                line_height=line_height,
            )
            continue

        editable_field: InlineField = segment
        width = field_widths[editable_field.key]
        if cursor_x > x_start and cursor_x + width > x_right:
            cursor_y -= line_height
            cursor_x = x_start

        underline_y = cursor_y - 2
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(1)
        canvas.line(cursor_x, underline_y, cursor_x + width, underline_y)

        canvas.setFillColor(MUTED)
        canvas.setFont(normal_font, 4.5)
        canvas.drawString(cursor_x, cursor_y + 10, field_labels[editable_field.key].upper())

        placements.append(
            _FieldPlacement(
                key=editable_field.key,
                label=field_labels[editable_field.key],
                x=cursor_x,
                y=cursor_y - (field_height - 7) / 2,
                width=width,
                height=field_height,
                value=field_defaults[editable_field.key],
            )
        )

        canvas.setFillColor(INK)
        canvas.setFont(normal_font, body_font_size)
        cursor_x += width + pdfmetrics.stringWidth(" ", normal_font, body_font_size)

    return cursor_y - clause_gap, placements


def _draw_body(
    canvas: Canvas,
    template_parameters: object,
    template_definition: object,
    normal_font: str,
    bold_font: str,
    *,
    start_y: float,
) -> tuple[float, list[_FieldPlacement]]:
    clauses = template_definition.build_clauses(template_parameters)
    field_defaults = defaults_for_fields(template_parameters, template_definition.inline_editable_fields)
    resolved_labels = labels_for_fields(template_definition.inline_editable_fields)
    resolved_widths = widths_for_fields(template_definition.inline_editable_fields)

    cursor_y = start_y
    placements: list[_FieldPlacement] = []
    x_start = LEFT_MARGIN
    x_right = PAGE_WIDTH - RIGHT_MARGIN

    for clause in clauses:
        cursor_y, clause_placements = _draw_inline_clause(
            canvas,
            clause,
            field_defaults,
            resolved_labels,
            resolved_widths,
            x_start=x_start,
            x_right=x_right,
            start_y=cursor_y,
            normal_font=normal_font,
            bold_font=bold_font,
        )
        placements.extend(clause_placements)
        cursor_y -= 4

    note_text = template_definition.notes_line(template_parameters)
    if note_text:
        canvas.setFillColor(MUTED)
        cursor_y -= 8
        cursor_y = _draw_wrapped_text(
            canvas,
            note_text,
            LEFT_MARGIN,
            cursor_y,
            PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN,
            14,
            normal_font,
            9,
        )

    return cursor_y, placements


def _draw_form_fields(canvas: Canvas, placements: list[_FieldPlacement]) -> None:
    for placement in placements:
        canvas.acroForm.textfield(
            name=placement.key,
            tooltip=placement.label,
            x=placement.x,
            y=placement.y,
            width=placement.width,
            height=placement.height,
            borderWidth=0,
            borderStyle="solid",
            borderColor=LINE,
            fillColor=WHITE,
            textColor=INK,
            forceBorder=False,
            fontName="Helvetica",
            fontSize=0,
            value=placement.value,
        )


def _draw_signature_section(canvas: Canvas, normal_font: str, bold_font: str, start_y: float) -> tuple[float, float, float, float]:
    cursor_y = max(start_y - 22, BOTTOM_MARGIN + 70)

    canvas.setFillColor(INK)
    canvas.setFont(bold_font, 11)
    canvas.drawString(LEFT_MARGIN, cursor_y, "Signature")

    canvas.setFillColor(MUTED)
    canvas.setFont(normal_font, 9)
    canvas.drawString(LEFT_MARGIN, cursor_y - 14, "Sign below to accept this contract.")

    line_y = cursor_y - 56
    sig_x1 = LEFT_MARGIN
    sig_x2 = PAGE_WIDTH - RIGHT_MARGIN
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(1)
    canvas.line(sig_x1, line_y, sig_x2, line_y)

    canvas.setFillColor(MUTED)
    canvas.setFont(normal_font, 8)
    canvas.drawString(LEFT_MARGIN, line_y - 11, "SIGNATURE")

    return (sig_x1, line_y - 7, sig_x2, line_y + 16)


def _inject_signature_field(pdf_bytes: bytes, rect: tuple[float, float, float, float]) -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    page = writer.pages[-1]
    signature_rect = ArrayObject([FloatObject(rect[0]), FloatObject(rect[1]), FloatObject(rect[2]), FloatObject(rect[3])])
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


def generate_contract_pdf(request: ContractRequest, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    template_definition = get_template_definition(request.template)
    template_parameters = validate_template_parameters(template_definition, request.template_parameters)

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=letter)
    normal_font, bold_font = _register_fonts()
    canvas.setAuthor("Contract Generator")
    canvas.setTitle(str(getattr(template_parameters, "document_title", template_definition.description)))
    canvas.setSubject("Generated contract PDF")
    canvas.setCreator("contract-generator")
    canvas.setFont(normal_font, 10)

    title_top = _draw_generic_header(canvas, request.generic_parameters.header, normal_font)
    start_y = _draw_header(canvas, template_parameters, normal_font, bold_font, title_top)
    end_of_body_y, placements = _draw_body(
        canvas,
        template_parameters,
        template_definition,
        normal_font,
        bold_font,
        start_y=start_y,
    )
    _draw_form_fields(canvas, placements)
    signature_rect = _draw_signature_section(canvas, normal_font, bold_font, end_of_body_y)
    _draw_generic_footer(canvas, request.generic_parameters.footer, normal_font)

    canvas.showPage()
    canvas.save()

    output.write_bytes(_inject_signature_field(buffer.getvalue(), signature_rect))
    return output
