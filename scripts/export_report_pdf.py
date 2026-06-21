from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "CS599_大作业报告.md"
OUTPUT = ROOT / "docs" / "CS599_大作业报告.pdf"
FONT_PATH = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")


class BookmarkParagraph(Paragraph):
    last_outline_level = -1

    def __init__(self, text: str, style: ParagraphStyle, key: str, level: int) -> None:
        super().__init__(text, style)
        self.key = key
        self.level = level

    def draw(self) -> None:
        canvas = self.canv
        canvas.bookmarkPage(self.key)
        requested_level = max(self.level - 1, 0)
        outline_level = min(requested_level, BookmarkParagraph.last_outline_level + 1)
        canvas.addOutlineEntry(self.getPlainText(), self.key, level=outline_level, closed=False)
        BookmarkParagraph.last_outline_level = outline_level
        super().draw()


def main() -> None:
    register_fonts()
    BookmarkParagraph.last_outline_level = -1
    styles = build_styles()
    story = markdown_to_story(SOURCE.read_text(encoding="utf-8"), styles)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="CS599 大作业报告",
        author="Software Engineer Agent",
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    print(OUTPUT)


def register_fonts() -> None:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont("ReportFont", str(FONT_PATH)))
        pdfmetrics.registerFont(TTFont("ReportFontBold", str(FONT_PATH)))
    else:
        pdfmetrics.registerFont(TTFont("ReportFont", "C:/Windows/Fonts/simhei.ttf"))
        pdfmetrics.registerFont(TTFont("ReportFontBold", "C:/Windows/Fonts/simhei.ttf"))


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    normal = ParagraphStyle(
        "ReportNormal",
        parent=base["Normal"],
        fontName="ReportFont",
        fontSize=10.5,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=normal,
            fontName="ReportFontBold",
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=normal,
            fontName="ReportFontBold",
            fontSize=16,
            leading=22,
            spaceBefore=10,
            spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "ReportH3",
            parent=normal,
            fontName="ReportFontBold",
            fontSize=13,
            leading=18,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "h4": ParagraphStyle(
            "ReportH4",
            parent=normal,
            fontName="ReportFontBold",
            fontSize=11.5,
            leading=17,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "normal": normal,
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=normal,
            leftIndent=12,
            firstLineIndent=-8,
        ),
        "code": ParagraphStyle(
            "ReportCode",
            parent=normal,
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1f2933"),
            backColor=colors.HexColor("#f5f7fa"),
            borderPadding=5,
            spaceBefore=4,
            spaceAfter=6,
        ),
    }


def markdown_to_story(markdown: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    lines = markdown.splitlines()
    index = 0
    in_code = False
    code_lines: list[str] = []
    heading_index = 0

    while index < len(lines):
        line = lines[index]
        if line.strip().startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not line.strip():
            story.append(Spacer(1, 4))
            index += 1
            continue

        if _is_table_start(lines, index):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(build_table(table_lines, styles))
            story.append(Spacer(1, 6))
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            text = clean_inline(heading.group(2))
            heading_index += 1
            key = f"heading-{heading_index}"
            if level == 1:
                story.append(BookmarkParagraph(text, styles["title"], key, 1))
            elif level == 2:
                story.append(BookmarkParagraph(text, styles["h2"], key, 2))
            elif level == 3:
                story.append(BookmarkParagraph(text, styles["h3"], key, 3))
            else:
                story.append(BookmarkParagraph(text, styles["h4"], key, 4))
            if text == "目录":
                story.append(PageBreak())
            index += 1
            continue

        if line.strip().startswith("- "):
            story.append(Paragraph("• " + clean_inline(line.strip()[2:]), styles["bullet"]))
            index += 1
            continue

        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            if not next_line.strip() or next_line.startswith("#") or next_line.strip().startswith(("```", "- ", "|")):
                break
            paragraph_lines.append(next_line.strip())
            index += 1
        story.append(Paragraph(clean_inline(" ".join(paragraph_lines)), styles["normal"]))

    return story


def build_table(table_lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for line in table_lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append([Paragraph(clean_inline(cell), styles["normal"]) for cell in cells])

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "ReportFont"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa5b1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def clean_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text.replace("&", "&amp;").replace("<font", "<font").replace("</font>", "</font>")


def _is_table_start(lines: list[str], index: int) -> bool:
    return lines[index].strip().startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|")


def draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("ReportFont", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    main()
