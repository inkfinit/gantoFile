"""Offline OCR classification and reconstruction for scanned and hybrid PDFs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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


def _get_page_image_rects(page: fitz.Page) -> List[fitz.Rect]:
    """Return deduplicated, page-clipped bounding boxes of all images on a page."""
    page_rect = page.rect
    seen = set()
    rects: List[fitz.Rect] = []

    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:
        infos = []

    for info in infos:
        bbox = info.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        clipped = fitz.Rect(bbox) & page_rect
        if clipped.is_empty or clipped.width <= 1.0 or clipped.height <= 1.0:
            continue
        key = (
            round(float(clipped.x0) / 2.0),
            round(float(clipped.y0) / 2.0),
            round(float(clipped.x1) / 2.0),
            round(float(clipped.y1) / 2.0),
        )
        if key not in seen:
            seen.add(key)
            rects.append(clipped)

    if not rects:
        for img in page.get_images(full=False):
            xref = img[0]
            try:
                img_rects = page.get_image_rects(xref)
            except Exception:
                img_rects = []
            for rect in img_rects:
                clipped = rect & page_rect
                if clipped.is_empty or clipped.width <= 1.0 or clipped.height <= 1.0:
                    continue
                key = (
                    round(float(clipped.x0) / 2.0),
                    round(float(clipped.y0) / 2.0),
                    round(float(clipped.x1) / 2.0),
                    round(float(clipped.y1) / 2.0),
                )
                if key not in seen:
                    seen.add(key)
                    rects.append(clipped)

    return rects


def _candidate_hybrid_rects(img_rects: List[fitz.Rect]) -> List[fitz.Rect]:
    """Filter image rects large enough to realistically contain document text."""
    return [r for r in img_rects if float(r.width) >= 60.0 and float(r.height) >= 20.0]


def classify_page_ocr(page: fitz.Page, force_ocr: bool = False) -> str:
    """Classify a PDF page as 'full_page', 'hybrid_images', or 'none'."""
    if force_ocr:
        return "full_page"

    text_len = len(page.get_text("text").strip())
    page_rect = page.rect
    page_area = max(1.0, float(page_rect.width) * float(page_rect.height))
    img_rects = _get_page_image_rects(page)

    areas = [max(0.0, float(r.width) * float(r.height)) for r in img_rects]
    max_img_ratio = (max(areas) / page_area) if areas else 0.0
    total_img_ratio = min(1.0, sum(areas) / page_area) if areas else 0.0

    # Full-page OCR: image-only scan, vector-outlined text, or scan with hidden text layer/watermark
    if text_len < 30:
        if img_rects:
            return "full_page"
        try:
            drawings = page.get_drawings()
            drawing_items = sum(len(d.get("items", ())) for d in drawings)
            if len(drawings) > 15 or drawing_items > 15:
                return "full_page"
        except Exception:
            pass

    if max_img_ratio >= 0.75:
        return "full_page"

    if total_img_ratio >= 0.55 and text_len < 150:
        return "full_page"

    if _candidate_hybrid_rects(img_rects):
        return "hybrid_images"

    return "none"


def plan_ocr_pages(input_path: Path, force_ocr: bool = False) -> Tuple[int, Dict[int, str]]:
    """Inspect every page and return (page_count, {page_index: ocr_mode})."""
    doc = fitz.open(str(input_path))
    try:
        plan: Dict[int, str] = {}
        for idx, page in enumerate(doc):
            mode = classify_page_ocr(page, force_ocr=force_ocr)
            if mode != "none":
                plan[idx] = mode
        return doc.page_count, plan
    finally:
        doc.close()


def _compute_render_dpi(
    width_pt: float,
    height_pt: float,
    target_dpi: int = 260,
    max_side_px: int = 2800,
) -> int:
    """Compute an adaptive DPI that preserves small text while capping huge dimensions."""
    max_pt = max(1.0, float(width_pt), float(height_pt))
    max_inches = max_pt / 72.0
    if max_inches * target_dpi <= max_side_px:
        return target_dpi
    return max(140, int(max_side_px / max_inches))


def _filter_ocr_detections(
    detections: Optional[List[Any]],
    scale: float,
    min_score: float,
) -> List[Tuple[int, float, float, float, float, str]]:
    """Parse, filter, normalize, and top-to-bottom sort RapidOCR detections."""
    if not detections:
        return []

    parsed: List[Tuple[int, float, float, float, float, str]] = []
    for item in detections:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, raw_text, raw_score = item[0], item[1], item[2]
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        if score < min_score or not isinstance(raw_text, str):
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
        parsed.append((round(y0 / 4.0), x0, x1, y0, y1, clean_text))

    parsed.sort(key=lambda entry: (entry[0], entry[1]))
    return parsed


def _insert_ocr_detections(
    target_page: fitz.Page,
    parsed_boxes: List[Tuple[int, float, float, float, float, str]],
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> int:
    """Insert OCR text boxes onto target_page at layout coordinates."""
    page_w = float(target_page.rect.width)
    page_h = float(target_page.rect.height)
    inserted = 0

    for _, x0, x1, y0, y1, clean_text in parsed_boxes:
        box_w = max(1.0, x1 - x0)
        box_h = max(1.0, y1 - y0)
        fontsize = max(7.0, min(36.0, box_h * 0.82))

        text_w = fitz.get_text_length(clean_text, fontname="helv", fontsize=fontsize)
        if text_w > box_w * 1.12 and text_w > 0.0:
            fontsize = max(6.0, fontsize * (box_w * 1.12 / text_w))

        insert_x = max(2.0, min(page_w - 10.0, offset_x + x0))
        baseline_y = offset_y + y0 + min(box_h * 0.85, fontsize * 0.92)
        baseline_y = max(fontsize, min(page_h - 2.0, baseline_y))

        target_page.insert_text(
            (insert_x, baseline_y),
            clean_text,
            fontname="helv",
            fontsize=fontsize,
            color=(0, 0, 0),
        )
        inserted += 1

    return inserted


def reconstruct_pdf_with_ocr(
    input_path: Path,
    output_pdf_path: Path,
    force_ocr: bool = False,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Tuple[int, int]:
    """Reconstruct scanned pages and embedded text-images into searchable PDF text."""
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    src_doc = fitz.open(str(input_path))
    out_doc = fitz.open()
    ocr_engine: Optional[RapidOCR] = None

    try:
        modes = [classify_page_ocr(page, force_ocr=force_ocr) for page in src_doc]
        total_work = sum(1 for m in modes if m != "none")
        done_work = 0
        ocr_pages = 0
        ocr_images_replaced = 0

        for idx, page in enumerate(src_doc):
            mode = modes[idx]
            if mode == "none":
                out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                continue

            if ocr_engine is None:
                ocr_engine = RapidOCR()

            if mode == "full_page":
                render_dpi = _compute_render_dpi(page.rect.width, page.rect.height)
                scale = 72.0 / float(render_dpi)
                pix = page.get_pixmap(dpi=render_dpi, colorspace=fitz.csRGB, alpha=False)
                img_rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, 3
                )
                img_bgr = np.ascontiguousarray(img_rgb[:, :, ::-1])
                result, _ = ocr_engine(img_bgr)

                out_page = out_doc.new_page(width=float(page.rect.width), height=float(page.rect.height))
                parsed = _filter_ocr_detections(result, scale=scale, min_score=0.35)
                _insert_ocr_detections(out_page, parsed)
                ocr_pages += 1

            elif mode == "hybrid_images":
                out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
                out_page = out_doc[-1]
                candidate_rects = _candidate_hybrid_rects(_get_page_image_rects(page))
                replacements: List[Tuple[fitz.Rect, List[Tuple[int, float, float, float, float, str]]]] = []

                for img_rect in candidate_rects:
                    render_dpi = _compute_render_dpi(img_rect.width, img_rect.height)
                    scale = 72.0 / float(render_dpi)
                    pix = page.get_pixmap(
                        dpi=render_dpi,
                        clip=img_rect,
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
                    if pix.width < 12 or pix.height < 12:
                        continue

                    img_rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, 3
                    )
                    img_bgr = np.ascontiguousarray(img_rgb[:, :, ::-1])
                    result, _ = ocr_engine(img_bgr)
                    parsed = _filter_ocr_detections(result, scale=scale, min_score=0.45)

                    total_chars = sum(len(entry[5].strip()) for entry in parsed)
                    if total_chars >= 8 or len(parsed) >= 2:
                        replacements.append((img_rect, parsed))

                if replacements:
                    for img_rect, _ in replacements:
                        out_page.add_redact_annot(img_rect, fill=None)

                    out_page.apply_redactions(
                        images=fitz.PDF_REDACT_IMAGE_REMOVE,
                        text=fitz.PDF_REDACT_TEXT_NONE,
                        graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                    )

                    for img_rect, parsed in replacements:
                        _insert_ocr_detections(
                            out_page,
                            parsed,
                            offset_x=float(img_rect.x0),
                            offset_y=float(img_rect.y0),
                        )

                    ocr_images_replaced += len(replacements)
                    ocr_pages += 1

            done_work += 1
            if progress_cb is not None:
                progress_cb(done_work, total_work)

        if ocr_pages > 0 or ocr_images_replaced > 0:
            out_doc.save(str(output_pdf_path))

        return ocr_pages, ocr_images_replaced
    finally:
        out_doc.close()
        src_doc.close()
