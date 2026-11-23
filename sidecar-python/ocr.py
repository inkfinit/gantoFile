"""Offline OCR reconstruction for scanned or image-based PDF pages."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Tuple

import fitz  # PyMuPDF

_SMART_PUNCT_TRANSLATION = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
        "\u25cf": "-",
        "\u25aa": "-",
    }
)


def _normalize_text_for_pdf(text: str) -> str:
    """Normalize smart punctuation and clamp to Latin-1 for built-in PDF fonts."""
    cleaned = " ".join(text.translate(_SMART_PUNCT_TRANSLATION).split())
    return cleaned.encode("latin-1", "replace").decode("latin-1")


def is_page_scanned(page: fitz.Page) -> bool:
    """Return True if the PDF page is image-only or primarily rasterized text."""
    images = page.get_images(full=False)
    if not images:
        return False

    text_len = len(page.get_text("text").strip())
    if text_len < 30:
        return True

    page_rect = page.rect
    page_area = max(1.0, float(page_rect.width) * float(page_rect.height))
    covered_area = 0.0
    for img in images:
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        for rect in rects:
            clipped = rect & page_rect
            if not clipped.is_empty:
                covered_area += max(0.0, float(clipped.width) * float(clipped.height))

    return (covered_area / page_area) >= 0.55 and text_len < 120


def detect_scanned_pages(input_path: Path) -> Tuple[int, List[int]]:
    """Inspect all pages and return (page_count, zero_based_scanned_indices)."""
    doc = fitz.open(str(input_path))
    try:
        scanned_indices = [idx for idx, page in enumerate(doc) if is_page_scanned(page)]
        return doc.page_count, scanned_indices
    finally:
        doc.close()


def reconstruct_pdf_with_ocr(
    input_path: Path,
    output_pdf_path: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    dpi: int = 220,
) -> int:
    """Reconstruct scanned PDF pages into a clean searchable layout PDF via RapidOCR."""
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    src_doc = fitz.open(str(input_path))
    out_doc = fitz.open()
    ocr_engine: Optional[RapidOCR] = None

    try:
        scanned_flags = [is_page_scanned(page) for page in src_doc]
        total_scanned = sum(1 for flag in scanned_flags if flag)
        done_scanned = 0
        scale = 72.0 / float(dpi)

        for idx, page in enumerate(src_doc):
            if not scanned_flags[idx]:
                out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                continue

            if ocr_engine is None:
                ocr_engine = RapidOCR()

            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            result, _ = ocr_engine(img)

            page_w = float(page.rect.width)
            page_h = float(page.rect.height)
            out_page = out_doc.new_page(width=page_w, height=page_h)

            if result:
                parsed_boxes = []
                for item in result:
                    if not isinstance(item, (list, tuple)) or len(item) < 3:
                        continue
                    box, raw_text, raw_score = item[0], item[1], item[2]
                    try:
                        score = float(raw_score)
                    except (TypeError, ValueError):
                        score = 0.0
                    if score < 0.35 or not isinstance(raw_text, str):
                        continue

                    clean_text = _normalize_text_for_pdf(raw_text)
                    if not clean_text:
                        continue

                    xs = [float(pt[0]) for pt in box]
                    ys = [float(pt[1]) for pt in box]
                    x0 = min(xs) * scale
                    x1 = max(xs) * scale
                    y0 = min(ys) * scale
                    y1 = max(ys) * scale
                    parsed_boxes.append((round(y0 / 4.0), x0, x1, y0, y1, clean_text))

                parsed_boxes.sort(key=lambda entry: (entry[0], entry[1]))

                for _, x0, x1, y0, y1, clean_text in parsed_boxes:
                    box_w = max(1.0, x1 - x0)
                    box_h = max(1.0, y1 - y0)
                    fontsize = max(7.0, min(36.0, box_h * 0.82))

                    text_w = fitz.get_text_length(clean_text, fontname="helv", fontsize=fontsize)
                    if text_w > box_w * 1.12 and text_w > 0.0:
                        fontsize = max(6.0, fontsize * (box_w * 1.12 / text_w))

                    insert_x = max(2.0, min(page_w - 10.0, x0))
                    baseline_y = y0 + min(box_h * 0.85, fontsize * 0.92)
                    baseline_y = max(fontsize, min(page_h - 2.0, baseline_y))

                    out_page.insert_text(
                        (insert_x, baseline_y),
                        clean_text,
                        fontname="helv",
                        fontsize=fontsize,
                        color=(0, 0, 0),
                    )

            done_scanned += 1
            if progress_cb is not None:
                progress_cb(done_scanned, total_scanned)

        out_doc.save(str(output_pdf_path))
        return total_scanned
    finally:
        out_doc.close()
        src_doc.close()
