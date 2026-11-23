"""Post-processing cleanup rules for DOCX documents generated from PDF."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List

from docx import Document
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.table import Table
from docx.text.paragraph import Paragraph

# Subset prefix added by PDF generators, e.g. ABCDEE+Calibri
_SUBSET_PREFIX_RE = re.compile(r"^[A-Z]{6}\+")

# Common PDF PostScript / Linux / subset font names -> standard cross-platform names
_FONT_ALIAS_MAP: Dict[str, str] = {
    "times": "Times New Roman",
    "timesnewroman": "Times New Roman",
    "timesnewromanps": "Times New Roman",
    "timesnewromanpsmt": "Times New Roman",
    "timesnewromanpsboldmt": "Times New Roman",
    "timesnewromanpsitalicmt": "Times New Roman",
    "timesnewromanpsbolditalicmt": "Times New Roman",
    "timesroman": "Times New Roman",
    "timesbold": "Times New Roman",
    "timesitalic": "Times New Roman",
    "timesbolditalic": "Times New Roman",
    "nimbusromno9l": "Times New Roman",
    "nimbusromno9lregu": "Times New Roman",
    "nimbusromno9lmedi": "Times New Roman",
    "nimbusroman": "Times New Roman",
    "arialmt": "Arial",
    "arialboldmt": "Arial",
    "arialitalicmt": "Arial",
    "arialbolditalicmt": "Arial",
    "helvetica": "Arial",
    "helveticabold": "Arial",
    "helveticaoblique": "Arial",
    "helveticaboldoblique": "Arial",
    "helveticaneue": "Arial",
    "nimbussanl": "Arial",
    "nimbussanlregu": "Arial",
    "liberationsans": "Arial",
    "liberationserif": "Times New Roman",
    "liberationmono": "Courier New",
    "couriernewpsmt": "Courier New",
    "couriernewpsboldmt": "Courier New",
    "couriernewpsitalicmt": "Courier New",
    "couriernewpsbolditalicmt": "Courier New",
    "courier": "Courier New",
    "courierbold": "Courier New",
    "courieroblique": "Courier New",
    "nimbusmonl": "Courier New",
    "carlito": "Calibri",
    "caladea": "Cambria",
    "trebuchetms": "Trebuchet MS",
    "bookantiqua": "Book Antiqua",
    "centurygothic": "Century Gothic",
    "palatinolinotype": "Palatino Linotype",
    "lucidasans": "Lucida Sans",
    "lucidaconsole": "Lucida Console",
    "segoeui": "Segoe UI",
    "microsoftsansserif": "Microsoft Sans Serif",
}

_STYLE_SUFFIX_RE = re.compile(
    r"(?:[-_, ]+(?:Regular|Roman|Medium|SemiBold|Semibold|Bold|Italic|Oblique|BoldItalic|BoldOblique|Light|Thin|Black|ExtraBold|Condensed)|(?:PS)?(?:Bold|Italic|Oblique)?MT)$",
    re.IGNORECASE,
)

# Common Symbol/Wingdings Private-Use-Area bullet codes -> clean Unicode
_PUA_SYMBOL_MAP: Dict[str, str] = {
    "\uf0b7": "•",
    "\uf0a7": "▪",
    "\uf076": "❖",
    "\uf0d8": "➢",
    "\uf0fc": "✓",
    "\uf0a8": "☐",
    "\uf0fe": "☑",
    "\uf06e": "■",
    "\uf06f": "○",
    "\uf0a0": " ",
}

_CONTROL_AND_ARTIFACTS_RE = re.compile(
    r"[\ufffd\u200b-\u200d\ufeff\u00ad\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)
_REMAINING_PUA_RE = re.compile(r"[\ue000-\uf8ff]")


@dataclass
class CleanOptions:
    """Configuration flags for DOCX post-processing."""

    normalize_fonts: bool = True
    strip_empty_lines: bool = True
    clean_encoding: bool = True
    preserve_layout_tables: bool = True


def _normalize_font_name(raw_name: str) -> str:
    """Convert embedded PDF font names into clean desktop font family names."""
    if not raw_name:
        return raw_name

    name = _SUBSET_PREFIX_RE.sub("", raw_name).strip()
    if not name:
        return raw_name

    # Remove style suffixes repeatedly (e.g. Arial-BoldMT -> Arial)
    cleaned = name
    for _ in range(3):
        next_cleaned = _STYLE_SUFFIX_RE.sub("", cleaned).strip(" -_,")
        if next_cleaned == cleaned or not next_cleaned:
            break
        cleaned = next_cleaned

    key = re.sub(r"[^a-z0-9]", "", cleaned.lower())
    if key in _FONT_ALIAS_MAP:
        return _FONT_ALIAS_MAP[key]

    raw_key = re.sub(r"[^a-z0-9]", "", name.lower())
    if raw_key in _FONT_ALIAS_MAP:
        return _FONT_ALIAS_MAP[raw_key]

    return cleaned or name


def _clean_text_string(text: str) -> tuple[str, int]:
    """Strip broken encoding artifacts and map stray PUA symbols."""
    if not text:
        return text, 0

    stripped_count = 0
    out = text

    for pua_char, replacement in _PUA_SYMBOL_MAP.items():
        if pua_char in out:
            stripped_count += out.count(pua_char)
            out = out.replace(pua_char, replacement)

    out, ctrl_hits = _CONTROL_AND_ARTIFACTS_RE.subn("", out)
    stripped_count += ctrl_hits

    out, pua_hits = _REMAINING_PUA_RE.subn("", out)
    stripped_count += pua_hits

    return out, stripped_count


def _iter_tables_recursive(tables: Iterable[Table]) -> Iterable[Table]:
    """Yield tables and any nested tables recursively."""
    for table in tables:
        yield table
        for row in table.rows:
            for cell in row.cells:
                yield from _iter_tables_recursive(cell.tables)


def _iter_all_paragraphs(doc: Document) -> Iterable[Paragraph]:
    """Yield every paragraph across body, tables, headers, and footers."""
    yield from doc.paragraphs

    for table in _iter_tables_recursive(doc.tables):
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs

    for section in doc.sections:
        for container in (
            section.header,
            section.first_page_header,
            section.even_page_header,
            section.footer,
            section.first_page_footer,
            section.even_page_footer,
        ):
            if container is None:
                continue
            yield from container.paragraphs
            for table in _iter_tables_recursive(container.tables):
                for row in table.rows:
                    for cell in row.cells:
                        yield from cell.paragraphs


def _paragraph_has_non_text_content(paragraph: Paragraph) -> bool:
    """Return True if a paragraph contains drawings, breaks, fields, or objects."""
    el = paragraph._element
    for tag in ("w:drawing", "w:pict", "w:object", "w:br", "w:fldSimple", "w:fldChar"):
        if el.find(f".//{tag}", el.nsmap) is not None:
            return True
    return False


def _set_run_font(run, font_name: str) -> None:
    """Apply normalized font name to run and its XML rFonts attributes."""
    run.font.name = font_name
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    r_fonts.set(qn("w:ascii"), font_name)
    r_fonts.set(qn("w:hAnsi"), font_name)
    r_fonts.set(qn("w:cs"), font_name)
    if r_fonts.get(qn("w:eastAsia")):
        r_fonts.set(qn("w:eastAsia"), font_name)


def _has_visible_borders(border_el) -> bool:
    """Check whether a tblBorders or tcBorders element has any visible border."""
    if border_el is None:
        return False
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        side_el = border_el.find(qn(f"w:{side}"))
        if side_el is not None:
            val = side_el.get(qn("w:val"))
            if val is not None and val.lower() not in ("none", "nil"):
                return True
    return False


def _ensure_invisible_table_layout(table: Table) -> bool:
    """Ensure borderless layout tables explicitly stay borderless in Word/LibreOffice."""
    tbl_el = table._tbl
    tbl_pr = tbl_el.tblPr
    if tbl_pr is None:
        return False

    tbl_borders = tbl_pr.find(qn("w:tblBorders"))
    if _has_visible_borders(tbl_borders):
        return False

    # Check if any cell defines explicit visible borders
    for tc in tbl_el.findall(f".//{qn('w:tc')}"):
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is not None and _has_visible_borders(tc_pr.find(qn("w:tcBorders"))):
            return False

    # Explicitly write nil borders so Word/LibreOffice never auto-draws grid lines
    if tbl_borders is not None:
        tbl_pr.remove(tbl_borders)

    nil_borders_xml = (
        f"<w:tblBorders {nsdecls('w')}>"
        '<w:top w:val="nil"/>'
        '<w:left w:val="nil"/>'
        '<w:bottom w:val="nil"/>'
        '<w:right w:val="nil"/>'
        '<w:insideH w:val="nil"/>'
        '<w:insideV w:val="nil"/>'
        "</w:tblBorders>"
    )
    tbl_pr.append(parse_xml(nil_borders_xml))

    # Preserve fixed layout when grid columns exist
    if tbl_pr.find(qn("w:tblLayout")) is None and tbl_el.find(qn("w:tblGrid")) is not None:
        tbl_pr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))

    return True


def clean_docx(docx_path: str, options: CleanOptions | None = None) -> Dict[str, int]:
    """Apply post-processing cleanup rules to a generated DOCX file in place."""
    if options is None:
        options = CleanOptions()

    doc = Document(docx_path)
    stats: Dict[str, int] = {
        "fonts_normalized": 0,
        "empty_paragraphs_removed": 0,
        "artifacts_stripped": 0,
        "tables_processed": 0,
    }

    if options.normalize_fonts:
        normal_style = doc.styles["Normal"] if "Normal" in doc.styles else None
        if normal_style is not None and normal_style.font.name:
            normalized = _normalize_font_name(normal_style.font.name)
            if normalized != normal_style.font.name:
                normal_style.font.name = normalized
                stats["fonts_normalized"] += 1

    # 1. Clean encoding artifacts and normalize fonts on all runs
    for paragraph in _iter_all_paragraphs(doc):
        for run in paragraph.runs:
            if options.clean_encoding:
                for t_el in run._element.findall(qn("w:t")):
                    if t_el.text:
                        cleaned_text, hits = _clean_text_string(t_el.text)
                        if hits > 0:
                            t_el.text = cleaned_text
                            stats["artifacts_stripped"] += hits

            if options.normalize_fonts:
                current_font = run.font.name
                if not current_font:
                    r_pr = run._element.rPr
                    if r_pr is not None:
                        r_fonts = r_pr.find(qn("w:rFonts"))
                        if r_fonts is not None:
                            current_font = (
                                r_fonts.get(qn("w:ascii"))
                                or r_fonts.get(qn("w:hAnsi"))
                                or r_fonts.get(qn("w:cs"))
                            )
                if current_font:
                    normalized = _normalize_font_name(current_font)
                    if normalized and normalized != current_font:
                        _set_run_font(run, normalized)
                        stats["fonts_normalized"] += 1

        # Trim trailing whitespace on the last text element of each paragraph
        if options.strip_empty_lines and paragraph.runs:
            t_elements = paragraph._element.findall(f".//{qn('w:t')}")
            if t_elements:
                last_t = t_elements[-1]
                if last_t.text and last_t.text != last_t.text.rstrip(" \t"):
                    last_t.text = last_t.text.rstrip(" \t")

    # 2. Collapse consecutive redundant empty top-level body paragraphs
    if options.strip_empty_lines:
        consecutive_empty = 0
        to_remove: List = []
        for paragraph in doc.paragraphs:
            has_text = bool(paragraph.text and paragraph.text.strip())
            if not has_text and not _paragraph_has_non_text_content(paragraph):
                consecutive_empty += 1
                if consecutive_empty > 1:
                    to_remove.append(paragraph._element)
            else:
                consecutive_empty = 0

        for p_el in to_remove:
            parent = p_el.getparent()
            if parent is not None:
                parent.remove(p_el)
                stats["empty_paragraphs_removed"] += 1

    # 3. Preserve invisible layout tables (e.g. signature blocks, letterheads)
    if options.preserve_layout_tables:
        all_tables = list(_iter_tables_recursive(doc.tables))
        for section in doc.sections:
            for container in (
                section.header,
                section.first_page_header,
                section.even_page_header,
                section.footer,
                section.first_page_footer,
                section.even_page_footer,
            ):
                if container is not None:
                    all_tables.extend(_iter_tables_recursive(container.tables))

        for table in all_tables:
            if _ensure_invisible_table_layout(table):
                stats["tables_processed"] += 1

    doc.save(docx_path)
    return stats
