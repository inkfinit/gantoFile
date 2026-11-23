"""GantoFile PDF-to-DOCX offline conversion sidecar CLI."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import logging
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF

# Configure logging before importing pdf2docx, which calls basicConfig(INFO) at import time
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)

from pdf2docx import Converter

from cleaner import CleanOptions, clean_docx
from ocr import is_page_scanned, reconstruct_pdf_with_ocr

_REAL_STDOUT = sys.stdout


def emit(payload: Dict[str, Any]) -> None:
    """Emit a single JSON event line to stdout and flush immediately."""
    _REAL_STDOUT.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _REAL_STDOUT.flush()


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Parse sidecar CLI arguments."""
    parser = argparse.ArgumentParser(description="GantoFile offline PDF-to-DOCX conversion engine")
    parser.add_argument("--input", required=True, help="Path to the source PDF file")
    parser.add_argument("--output", required=True, help="Path to the output DOCX file")
    parser.add_argument(
        "--normalize-fonts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Normalize embedded PDF font names to standard system fonts",
    )
    parser.add_argument(
        "--strip-empty-lines",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Collapse consecutive empty paragraphs and trailing whitespace",
    )
    parser.add_argument(
        "--clean-encoding",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Strip broken encodings, replacement characters, and control artifacts",
    )
    parser.add_argument(
        "--preserve-layout-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Ensure borderless layout tables remain invisible in Word/LibreOffice",
    )
    parser.add_argument(
        "--ocr-scanned",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run offline ONNX OCR on scanned or image-based PDF pages",
    )
    return parser.parse_args(argv)


def inspect_pdf(input_path: Path, ocr_enabled: bool) -> Tuple[int, List[int], List[Dict[str, str]]]:
    """Validate PDF readability, page count, and detect scanned/image-only pages."""
    warnings: List[Dict[str, str]] = []
    doc = fitz.open(str(input_path))
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            emit(
                {
                    "event": "error",
                    "code": "ENCRYPTED_PDF",
                    "message": "This PDF is password-protected or encrypted and cannot be converted.",
                }
            )
            sys.exit(1)

        page_count = doc.page_count
        if page_count == 0:
            emit(
                {
                    "event": "error",
                    "code": "EMPTY_PDF",
                    "message": "This PDF has zero pages.",
                }
            )
            sys.exit(1)

        scanned_indices = [idx for idx, page in enumerate(doc) if is_page_scanned(page)]

        if scanned_indices and not ocr_enabled:
            warning = {
                "event": "warning",
                "code": "SCANNED_PDF",
                "message": (
                    "This PDF appears to contain scanned images with limited selectable text. "
                    "Offline OCR is disabled, so the converted DOCX may contain embedded images."
                ),
            }
            emit(warning)
            warnings.append({"code": warning["code"], "message": warning["message"]})

        return page_count, scanned_indices, warnings
    finally:
        doc.close()


def _convert_pdf_to_docx(pdf_path: Path, output_path: Path) -> None:
    """Run pdf2docx conversion while keeping noisy library prints off stdout."""
    with redirect_stdout(sys.stderr):
        cv = Converter(str(pdf_path))
        try:
            cv.convert(str(output_path), start=0, end=None)
        finally:
            cv.close()


def main(argv: List[str] | None = None) -> None:
    """Run PDF inspection, optional offline OCR reconstruction, pdf2docx, and cleanup."""
    args = parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists() or not input_path.is_file():
        emit(
            {
                "event": "error",
                "code": "INPUT_NOT_FOUND",
                "message": f"Input PDF not found: {input_path}",
            }
        )
        sys.exit(1)

    if input_path.suffix.lower() != ".pdf":
        emit(
            {
                "event": "error",
                "code": "INVALID_INPUT",
                "message": "Only .pdf files can be converted.",
            }
        )
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        emit(
            {
                "event": "progress",
                "percent": 10,
                "stage": "inspecting",
                "message": "Inspecting PDF structure and fonts...",
            }
        )
        page_count, scanned_indices, warnings = inspect_pdf(input_path, args.ocr_scanned)

        ocr_pages = 0
        if scanned_indices and args.ocr_scanned:
            total_scanned = len(scanned_indices)
            emit(
                {
                    "event": "progress",
                    "percent": 20,
                    "stage": "ocr",
                    "message": f"Detected {total_scanned} image-based page(s). Running offline OCR...",
                }
            )
            with tempfile.TemporaryDirectory(prefix="gantofile_ocr_") as tmp_dir:
                ocr_pdf_path = Path(tmp_dir) / "ocr_reconstructed.pdf"

                def _on_ocr_progress(done: int, total: int) -> None:
                    pct = 20 + int((done / max(1, total)) * 35)
                    emit(
                        {
                            "event": "progress",
                            "percent": pct,
                            "stage": "ocr",
                            "message": f"Extracting text via offline OCR ({done}/{total} page(s))...",
                        }
                    )

                with redirect_stdout(sys.stderr):
                    ocr_pages = reconstruct_pdf_with_ocr(
                        input_path,
                        ocr_pdf_path,
                        progress_cb=_on_ocr_progress,
                    )

                emit(
                    {
                        "event": "progress",
                        "percent": 55,
                        "stage": "converting",
                        "message": f"Building DOCX layout for {page_count} page(s)...",
                    }
                )
                _convert_pdf_to_docx(ocr_pdf_path, output_path)
        else:
            emit(
                {
                    "event": "progress",
                    "percent": 30,
                    "stage": "converting",
                    "message": f"Converting {page_count} page(s) to DOCX layout...",
                }
            )
            _convert_pdf_to_docx(input_path, output_path)

        emit(
            {
                "event": "progress",
                "percent": 80,
                "stage": "cleaning",
                "message": "Normalizing typography, encoding, and layout tables...",
            }
        )

        options = CleanOptions(
            normalize_fonts=args.normalize_fonts,
            strip_empty_lines=args.strip_empty_lines,
            clean_encoding=args.clean_encoding,
            preserve_layout_tables=args.preserve_layout_tables,
        )
        stats = clean_docx(str(output_path), options)
        stats["ocr_pages"] = ocr_pages

        emit(
            {
                "event": "done",
                "percent": 100,
                "output_path": str(output_path),
                "pages": page_count,
                "warnings": warnings,
                "stats": stats,
            }
        )
    except SystemExit:
        raise
    except Exception as exc:
        emit(
            {
                "event": "error",
                "code": "CONVERSION_FAILED",
                "message": str(exc) or "Conversion failed unexpectedly.",
            }
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
