"""Ganto PDF-to-DOCX offline conversion sidecar CLI."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List

import fitz  # PyMuPDF

# Configure logging before importing pdf2docx, which calls basicConfig(INFO) at import time
logging.basicConfig(stream=sys.stderr, level=logging.WARNING, force=True)

from pdf2docx import Converter

from cleaner import CleanOptions, clean_docx

_REAL_STDOUT = sys.stdout


def emit(payload: Dict[str, Any]) -> None:
    """Emit a single JSON event line to stdout and flush immediately."""
    _REAL_STDOUT.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _REAL_STDOUT.flush()


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    """Parse sidecar CLI arguments."""
    parser = argparse.ArgumentParser(description="Ganto offline PDF-to-DOCX conversion engine")
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
    return parser.parse_args(argv)


def inspect_pdf(input_path: Path) -> tuple[int, List[Dict[str, str]]]:
    """Validate PDF readability, page count, and detect scanned/image-only PDFs."""
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

        scanned_pages = 0
        for page in doc:
            text_len = len(page.get_text("text").strip())
            images = page.get_images(full=False)
            if text_len < 20 and len(images) > 0:
                scanned_pages += 1

        if scanned_pages > 0 and scanned_pages >= (page_count / 2):
            warning = {
                "event": "warning",
                "code": "SCANNED_PDF",
                "message": (
                    "This PDF appears to contain scanned images with limited selectable text. "
                    "The converted DOCX may contain embedded images rather than editable text."
                ),
            }
            emit(warning)
            warnings.append({"code": warning["code"], "message": warning["message"]})

        return page_count, warnings
    finally:
        doc.close()


def main(argv: List[str] | None = None) -> None:
    """Run PDF inspection, pdf2docx conversion, and post-processing cleanup."""
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
        page_count, warnings = inspect_pdf(input_path)

        emit(
            {
                "event": "progress",
                "percent": 30,
                "stage": "converting",
                "message": f"Converting {page_count} page(s) to DOCX layout...",
            }
        )

        # Redirect noisy third-party prints to stderr so stdout remains valid JSONL
        with redirect_stdout(sys.stderr):
            cv = Converter(str(input_path))
            try:
                cv.convert(str(output_path), start=0, end=None)
            finally:
                cv.close()

        emit(
            {
                "event": "progress",
                "percent": 75,
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
