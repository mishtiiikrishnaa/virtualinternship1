"""Render the report markdown to a formatted .docx.

Pandoc does the conversion; this module does the typography that a Word
submission is judged on: margins, heading hierarchy, table rules, code
shading, a footer with page numbers, and a table of contents whose page
numbers are measured from a rendered PDF rather than guessed.

    python -m src.build_report
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "week1_blueprint.md"
OUTPUT = ROOT / "reports" / "Week1_Strategic_Data_Collection_and_Preprocessing_Blueprint.docx"

INK = "1F2933"
ACCENT = "1F4E5F"
MUTED = "5C6B7A"
RULE = "D8DEE4"
CODE_BG = "F3F4F6"

BODY_FONT = "Calibri"
MONO_FONT = "Consolas"

PAGE_WIDTH_CM = 21.0
MARGIN_CM = 2.2
TEXT_WIDTH_CM = PAGE_WIDTH_CM - 2 * MARGIN_CM


# --------------------------------------------------------------------------
# small xml helpers
# --------------------------------------------------------------------------


def _shade(element, fill: str) -> None:
    pr = element.get_or_add_pPr() if element.tag.endswith("}p") else element
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def _shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _cell_margins(table) -> None:
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, width in (("top", 40), ("bottom", 40), ("left", 80), ("right", 80)):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:w"), str(width))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tbl_pr.append(mar)


def _borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), RULE)
        borders.append(el)
    tbl_pr.append(borders)


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def _keep_with_next(paragraph) -> None:
    paragraph.paragraph_format.keep_with_next = True


def _field(paragraph, instruction: str, placeholder: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, sep, text, end):
        run._r.append(node)
    run.font.name = BODY_FONT
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string(MUTED)


# --------------------------------------------------------------------------
# styling
# --------------------------------------------------------------------------


def _style(doc, name: str, *, size=None, bold=None, italic=None, colour=None,
           before=None, after=None, spacing=None, align=None, font=None):
    style = doc.styles[name]
    if font:
        style.font.name = font
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if colour:
        style.font.color.rgb = RGBColor.from_string(colour)
    fmt = style.paragraph_format
    if before is not None:
        fmt.space_before = Pt(before)
    if after is not None:
        fmt.space_after = Pt(after)
    if spacing is not None:
        fmt.line_spacing = spacing
    if align is not None:
        fmt.alignment = align
    return style


def _typography(doc) -> None:
    section = doc.sections[0]
    section.page_width = Cm(PAGE_WIDTH_CM)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(MARGIN_CM)
    section.right_margin = Cm(MARGIN_CM)
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(2.0)
    section.different_first_page_header_footer = True

    _style(doc, "Normal", font=BODY_FONT)
    _style(doc, "Body Text", size=10.5, before=0, after=7, spacing=1.16)
    _style(doc, "First Paragraph", size=10.5, before=0, after=7, spacing=1.16)
    _style(doc, "Compact", size=10.5, before=0, after=3, spacing=1.12)
    _style(doc, "Title", size=26, bold=True, colour=ACCENT, before=150, after=6, font=BODY_FONT)
    _style(doc, "Subtitle", size=13, italic=True, colour=MUTED, before=0, after=10, font=BODY_FONT)
    _style(doc, "Author", size=12, bold=True, colour=INK, before=26, after=2, font=BODY_FONT)
    _style(doc, "Date", size=11, colour=MUTED, before=0, after=0, font=BODY_FONT)

    doc.styles["Title"].font.name = BODY_FONT

    for name, size, colour, before, after in (
        ("Heading 1", 16, ACCENT, 22, 7),
        ("Heading 2", 12.5, INK, 15, 5),
        ("Heading 3", 11, MUTED, 11, 4),
    ):
        style = _style(doc, name, size=size, bold=True, colour=colour, before=before, after=after, font=BODY_FONT)
        style.paragraph_format.keep_with_next = True

    _style(doc, "Image Caption", size=8.5, italic=True, colour=MUTED,
           before=8, after=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    _style(doc, "Captioned Figure", size=10, before=10, after=0,
           align=WD_ALIGN_PARAGRAPH.CENTER)
    _style(doc, "Table Caption", size=8.5, italic=True, colour=MUTED,
           before=10, after=12, align=WD_ALIGN_PARAGRAPH.CENTER)

    code = doc.styles["Source Code"]
    code.font.name = MONO_FONT
    code.font.size = Pt(8)
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(8)
    code.paragraph_format.left_indent = Cm(0.3)
    code.paragraph_format.line_spacing = 1.05

    doc.styles["Verbatim Char"].font.name = MONO_FONT
    doc.styles["Verbatim Char"].font.size = Pt(9)


def _tables(doc) -> None:
    for table in doc.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        _borders(table)
        _cell_margins(table)
        for index, row in enumerate(table.rows):
            cant_split = OxmlElement("w:cantSplit")
            row._tr.get_or_add_trPr().append(cant_split)
            if index == 0:
                _repeat_header(row)
            for cell in row.cells:
                if index == 0:
                    _shade_cell(cell, ACCENT)
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_before = Pt(1)
                    paragraph.paragraph_format.space_after = Pt(1)
                    paragraph.paragraph_format.line_spacing = 1.0
                    for run in paragraph.runs:
                        run.font.name = BODY_FONT
                        run.font.size = Pt(8.2)
                        if index == 0:
                            run.font.bold = True
                            run.font.color.rgb = RGBColor.from_string("FFFFFF")
                    # hold the table together: a header row stranded at the
                    # foot of a page is the least readable thing in a report
                    if index < len(table.rows) - 1:
                        paragraph.paragraph_format.keep_with_next = True


def _code_blocks(doc) -> None:
    for paragraph in doc.paragraphs:
        if paragraph.style.name == "Source Code":
            _shade(paragraph._p, CODE_BG)
            for run in paragraph.runs:
                # pandoc emits syntax-highlight character styles; override at
                # run level so the listing stays one legible colour
                run.font.name = MONO_FONT
                run.font.size = Pt(7.8)
                run.font.color.rgb = RGBColor.from_string(INK)


def _footer(doc) -> None:
    footer = doc.sections[0].footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Strategic Data Collection and Preprocessing Blueprint  ·  page ")
    run.font.name = BODY_FONT
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string(MUTED)
    _field(paragraph, "PAGE", "1")
    tail = paragraph.add_run(" of ")
    tail.font.name = BODY_FONT
    tail.font.size = Pt(8.5)
    tail.font.color.rgb = RGBColor.from_string(MUTED)
    _field(paragraph, "NUMPAGES", "1")


def _insert_after(anchor, text: str):
    from docx.text.paragraph import Paragraph

    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    paragraph = Paragraph(new_p, anchor._parent)
    paragraph.add_run(text)
    return paragraph


def _cover(doc) -> None:
    """Style the pandoc title block, add the repository line, close the page."""
    by_style = {p.style.name: p for p in doc.paragraphs}
    date = by_style.get("Date")
    if date is None:
        return

    previous = date
    for text in (
        "Week 1 task submission  ·  virtual internship",
        "Repository: github.com/mishtiiikrishnaa/virtualinternship1",
    ):
        line = _insert_after(previous, text)
        line.alignment = WD_ALIGN_PARAGRAPH.CENTER
        line.paragraph_format.space_before = Pt(16 if text.startswith("Week 1") else 0)
        line.paragraph_format.space_after = Pt(2)
        for run in line.runs:
            run.font.name = BODY_FONT
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor.from_string(MUTED)
        previous = line

    previous.add_run().add_break(WD_BREAK.PAGE)


# --------------------------------------------------------------------------
# table of contents
# --------------------------------------------------------------------------


def headings(path: Path = SOURCE) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,2})\s+(.*)$", line)
        if match:
            entries.append((len(match.group(1)), match.group(2).strip()))
    return entries


def _toc(doc, numbers: dict[str, int] | None) -> None:
    anchor = None
    for paragraph in doc.paragraphs:
        if paragraph.style.name == "Heading 1":
            anchor = paragraph
            break
    if anchor is None:
        return

    title = anchor.insert_paragraph_before("Contents", style="Heading 1")
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(8)

    entries = [(lvl, txt) for lvl, txt in headings() if not (lvl == 2 and txt.startswith("A."))]
    for position, (level, text) in enumerate(entries):
        page = "" if numbers is None else str(numbers.get(text, ""))
        paragraph = anchor.insert_paragraph_before("", style="Compact")
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(0.5)
        fmt.space_after = Pt(0.5)
        fmt.line_spacing = 0.86
        fmt.left_indent = Cm(0 if level == 1 else 0.55)
        fmt.tab_stops.add_tab_stop(
            Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        label = f"{text}\t{page}" if page else text
        run = paragraph.add_run(label)
        run.font.name = BODY_FONT
        run.font.size = Pt(9.2 if level == 1 else 8.4)
        run.font.bold = level == 1
        run.font.color.rgb = RGBColor.from_string(INK if level == 1 else MUTED)

    anchor.paragraph_format.page_break_before = True


# --------------------------------------------------------------------------
# render pipeline
# --------------------------------------------------------------------------


def _pandoc(target: Path) -> None:
    subprocess.run(
        [
            "pandoc",
            str(SOURCE),
            "--from=markdown+pipe_tables+backtick_code_blocks",
            "--resource-path=docs",
            "--output",
            str(target),
            "--metadata=lang:en-GB",
        ],
        cwd=ROOT,
        check=True,
    )


def _to_pdf(docx_path: Path, out_dir: Path) -> Path | None:
    """Convert to PDF for pagination measurement, if a converter exists."""
    if shutil.which("soffice") is None:
        return None
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
            check=True,
            capture_output=True,
            timeout=300,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    pdf = out_dir / f"{docx_path.stem}.pdf"
    return pdf if pdf.exists() else None


def _page_index(pdf_path: Path) -> dict[str, int]:
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], check=True, capture_output=True, text=True
    ).stdout
    pages = text.split("\f")

    body_start = 0
    for index, page in enumerate(pages):
        if "...." in page:
            body_start = index + 1

    def norm(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    numbers: dict[str, int] = {}
    for _level, title in headings():
        prefix = norm(title)[:28]
        for index in range(body_start, len(pages)):
            lines = [norm(line) for line in pages[index].splitlines()]
            if any(line.startswith(prefix) and "...." not in line for line in lines):
                numbers[title] = index + 1
                break
    return numbers


def build() -> Path:
    figures = ROOT / "docs" / "figures"
    needed = ["fig1_workflow.png", "fig2_pipeline.png", "fig3_missingness.png"]
    missing = [f for f in needed if not (figures / f).exists()]
    if missing:
        raise SystemExit(f"missing figures: {missing} — run python -m src.make_figures")

    workdir = Path(tempfile.mkdtemp(prefix="report-build-"))
    numbers: dict[str, int] | None = None

    for attempt in range(3):
        tmp_docx = workdir / f"pass{attempt}.docx"
        _pandoc(tmp_docx)

        doc = docx.Document(tmp_docx)
        _typography(doc)
        _cover(doc)
        _toc(doc, numbers)
        _tables(doc)
        _code_blocks(doc)
        _footer(doc)
        epoch = os.environ.get("SOURCE_DATE_EPOCH")
        if epoch:
            from datetime import datetime, timezone

            stamp = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            doc.core_properties.created = stamp
            doc.core_properties.modified = stamp
        doc.core_properties.title = "Strategic Data Collection and Preprocessing Blueprint"
        doc.core_properties.author = "Meghana Krishnakumar Nair"
        doc.core_properties.subject = "Week 1 task — public logistics data and Python preprocessing"
        doc.core_properties.keywords = "logistics, data engineering, pandas, reproducibility"
        doc.save(tmp_docx)

        pdf = _to_pdf(tmp_docx, workdir)
        if pdf is None:
            shutil.copy(tmp_docx, OUTPUT)
            print("note: LibreOffice not found, table of contents rendered without page numbers")
            break

        measured = _page_index(pdf)
        if numbers == measured or attempt == 2:
            shutil.copy(tmp_docx, OUTPUT)
            _to_pdf(OUTPUT, OUTPUT.parent)
            break
        numbers = measured

    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:,.0f} kB)")
    print(f"toc entries located: {len(numbers or {})}/{len(headings())}")
    shutil.rmtree(workdir, ignore_errors=True)
    return OUTPUT


if __name__ == "__main__":
    build()
