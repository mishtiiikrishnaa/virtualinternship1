"""Word document mechanics: styles, tables, code boxes, figures, page numbers.

Kept separate from the content so that the report builder reads as prose plus
data calls, and so the audit can rely on named paragraph styles when it counts
words.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x17, 0x36, 0x5D)
BLUE = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x59, 0x59, 0x59)
INK = RGBColor(0x1A, 0x1A, 0x1A)

BODY_FONT = "Calibri"
CODE_FONT = "Consolas"


def _shade(element, fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def _borders(paragraph, colour: str = "D5D5D5") -> None:
    pPr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "3")
        element.set(qn("w:color"), colour)
        borders.append(element)
    pPr.append(borders)


def _field(paragraph, instruction: str, placeholder: str = "1") -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def _compressed_png(path: Path) -> str:
    """Re-encode a chart as a 256-colour PNG for embedding.

    The figure files on disk stay as full-colour PNGs; this only shrinks the
    copy inside the .docx, where the upload limit matters. At 256 colours the
    difference is invisible at print size and the document halves in weight.
    """
    from PIL import Image

    image = Image.open(path).convert("RGB")
    image = image.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.FLOYDSTEINBERG)
    handle, temporary = tempfile.mkstemp(suffix=".png")
    os.close(handle)
    image.save(temporary, "PNG", optimize=True, compress_level=9, dpi=(200, 200))
    return temporary


class Report:
    def __init__(self) -> None:
        self.doc = Document()
        self.figure_number = 0
        self.table_number = 0
        self._setup_page()
        self._setup_styles()
        self._setup_footer()

    # -- setup ------------------------------------------------------------
    def _setup_page(self) -> None:
        section = self.doc.sections[0]
        section.page_height = Cm(29.7)
        section.page_width = Cm(21.0)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(1.9)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.header_distance = Cm(1.0)
        section.footer_distance = Cm(0.9)

    def _setup_styles(self) -> None:
        styles = self.doc.styles
        normal = styles["Normal"]
        normal.font.name = BODY_FONT
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = INK
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.12
        normal._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

        for name, size, colour, before, after in [
            ("Heading 1", 17, NAVY, 0, 10),
            ("Heading 2", 13.5, BLUE, 12, 5),
            ("Heading 3", 11.5, RGBColor(0x33, 0x33, 0x33), 9, 3),
        ]:
            style = styles[name]
            style.font.name = BODY_FONT
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = colour
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True

        body = styles.add_style("BodyText2", 1)
        body.base_style = styles["Normal"]
        body.font.size = Pt(10.5)
        body.paragraph_format.space_after = Pt(6)
        body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        caption = styles.add_style("FigCaption", 1)
        caption.base_style = styles["Normal"]
        caption.font.size = Pt(9)
        caption.font.bold = True
        caption.font.color.rgb = BLUE
        caption.paragraph_format.space_before = Pt(6)
        caption.paragraph_format.space_after = Pt(2)
        caption.paragraph_format.keep_with_next = True

        purpose = styles.add_style("FigurePurpose", 1)
        purpose.base_style = styles["Normal"]
        purpose.font.size = Pt(9)
        purpose.font.italic = True
        purpose.font.color.rgb = GREY
        purpose.paragraph_format.space_after = Pt(2)
        purpose.paragraph_format.keep_with_next = True

        code = styles.add_style("CodeBlock", 1)
        code.base_style = styles["Normal"]
        code.font.name = CODE_FONT
        code.font.size = Pt(8.2)
        code.font.color.rgb = RGBColor(0x20, 0x20, 0x20)
        code.paragraph_format.space_before = Pt(3)
        code.paragraph_format.space_after = Pt(3)
        code.paragraph_format.line_spacing = 1.0
        code.paragraph_format.left_indent = Cm(0.2)
        code.paragraph_format.keep_together = True

        table_text = styles.add_style("TableText", 1)
        table_text.base_style = styles["Normal"]
        table_text.font.size = Pt(8.3)
        table_text.paragraph_format.space_after = Pt(1)
        table_text.paragraph_format.space_before = Pt(1)
        table_text.paragraph_format.line_spacing = 1.0

        table_caption = styles.add_style("TableCaption", 1)
        table_caption.base_style = styles["Normal"]
        table_caption.font.size = Pt(9)
        table_caption.font.bold = True
        table_caption.font.color.rgb = BLUE
        table_caption.paragraph_format.space_before = Pt(8)
        table_caption.paragraph_format.space_after = Pt(3)
        table_caption.paragraph_format.keep_with_next = True

        reference = styles.add_style("ReferenceEntry", 1)
        reference.base_style = styles["Normal"]
        reference.font.size = Pt(9.5)
        reference.paragraph_format.space_after = Pt(4)

        bullet = styles["List Bullet"]
        bullet.font.name = BODY_FONT
        bullet.font.size = Pt(10.5)
        bullet.paragraph_format.space_after = Pt(3)
        bullet.paragraph_format.left_indent = Cm(0.7)

        numbered = styles["List Number"]
        numbered.font.name = BODY_FONT
        numbered.font.size = Pt(10.5)
        numbered.paragraph_format.space_after = Pt(3)

    def _setup_footer(self) -> None:
        footer = self.doc.sections[0].footer
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run("Mishti Krishna  |  Week 3  |  page ")
        run.font.size = Pt(8)
        run.font.color.rgb = GREY
        _field(paragraph, "PAGE")
        run = paragraph.add_run(" of ")
        run.font.size = Pt(8)
        run.font.color.rgb = GREY
        _field(paragraph, "NUMPAGES", "28")
        for r in paragraph.runs:
            r.font.size = Pt(8)
            r.font.color.rgb = GREY

    # -- text -------------------------------------------------------------
    def h1(self, text: str, page_break: bool = False) -> None:
        paragraph = self.doc.add_heading(text, level=1)
        paragraph.paragraph_format.page_break_before = page_break

    def h2(self, text: str) -> None:
        self.doc.add_heading(text, level=2)

    def h3(self, text: str) -> None:
        self.doc.add_heading(text, level=3)

    def p(self, text: str, keep_with_next: bool = False) -> None:
        """Body paragraph; text between double backticks is set in the code font."""
        paragraph = self.doc.add_paragraph(style="BodyText2")
        for index, part in enumerate(text.split("``")):
            if not part:
                continue
            run = paragraph.add_run(part)
            if index % 2 == 1:
                run.font.name = CODE_FONT
                run.font.size = Pt(9.2)
        if keep_with_next:
            paragraph.paragraph_format.keep_with_next = True

    def bullets(self, items: list[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Bullet")

    def numbered(self, items: list[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Number")

    def caption(self, text: str, kind: str = "Figure") -> int:
        if kind == "Figure":
            self.figure_number += 1
            number = self.figure_number
        else:
            self.table_number += 1
            number = self.table_number
        paragraph = self.doc.add_paragraph(f"{kind} {number}. {text}",
                                           style="FigCaption" if kind == "Figure"
                                           else "TableCaption")
        return number

    def purpose(self, text: str) -> None:
        self.doc.add_paragraph(text, style="FigurePurpose")

    def code(self, snippet: str) -> None:
        paragraph = self.doc.add_paragraph(style="CodeBlock")
        lines = snippet.split("\n")
        run = paragraph.add_run(lines[0])
        run.font.name = CODE_FONT
        for line in lines[1:]:
            run = paragraph.add_run()
            run.add_break(WD_BREAK.LINE)
            run.add_text(line)
            run.font.name = CODE_FONT
        _shade(paragraph._p.get_or_add_pPr(), "F4F6F8")
        _borders(paragraph)

    def image(self, path: Path, alt: str, width_cm: float = 16.0) -> None:
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(4)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.keep_with_next = True
        embedded = _compressed_png(path)
        try:
            inline = paragraph.add_run().add_picture(embedded, width=Cm(width_cm))
        finally:
            os.unlink(embedded)
        docPr = inline._inline.docPr
        docPr.set("descr", alt)
        docPr.set("title", alt[:120])

    def table(self, headers: list[str], rows: list[list[str]],
              widths: list[float] | None = None, font_size: float = 8.3,
              header_fill: str = "1F3864", zebra: bool = True) -> None:
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        total = sum(widths) if widths else 17.0
        table.columns  # touch
        header = table.rows[0]
        trPr = header._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        trPr.append(repeat)
        for i, text in enumerate(headers):
            cell = header.cells[i]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(text)
            run.bold = True
            run.font.size = Pt(font_size)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            run.font.name = BODY_FONT
            _shade(cell._tc.get_or_add_tcPr(), header_fill)
            paragraph.paragraph_format.space_after = Pt(1)
        for index, row in enumerate(rows):
            cells = table.add_row().cells
            trPr = table.rows[-1]._tr.get_or_add_trPr()
            cant = OxmlElement("w:cantSplit")
            trPr.append(cant)
            for i, value in enumerate(row):
                cell = cells[i]
                cell.text = ""
                paragraph = cell.paragraphs[0]
                run = paragraph.add_run(str(value))
                run.font.size = Pt(font_size)
                run.font.name = BODY_FONT
                if index % 2 == 1 and zebra:
                    _shade(cell._tc.get_or_add_tcPr(), "EEF3F9")
        if widths:
            for i, width in enumerate(widths):
                table.columns[i].width = Cm(width * 17.0 / total)
            for row in table.rows:
                for i, width in enumerate(widths):
                    row.cells[i].width = Cm(width * 17.0 / total)
        # spacing paragraph after the table
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(2)
        spacer.paragraph_format.line_spacing = 1.0
        for run in spacer.runs:
            run.font.size = Pt(4)

    def spacer(self, points: float = 4) -> None:
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(points)

    def save(self, path: Path) -> None:
        self.doc.core_properties.title = (
            "Exploratory Data Analysis and Visualization of Logistics Shipment Data")
        self.doc.core_properties.author = "Meghana Krishnakumar Nair"
        self.doc.core_properties.subject = "Week 2 - EDA and visualization in logistics"
        self.doc.core_properties.keywords = ("logistics, EDA, Python, matplotlib, "
                                             "seaborn, plotly, simulation")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path)
