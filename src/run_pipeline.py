from __future__ import annotations

import argparse

from build_review import build_review
from ocr_pages import ocr_pages
from pipeline_common import parse_pages
from render_pages import render_pages
from scan_candidates import scan_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PDF render, OCR, risk scan, and review report.")
    parser.add_argument("--pages", default="22", help="Comma/range page list, e.g. 22 or 1,4,16-27.")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--gpu", action="store_true", help="Ask PaddleOCR to use GPU when supported.")
    parser.add_argument(
        "--engine",
        choices=["auto", "paddle", "rapidocr"],
        default="rapidocr",
        help="OCR engine. auto tries PaddleOCR then RapidOCR fallback.",
    )
    args = parser.parse_args()

    pages = parse_pages(args.pages)
    render_pages(pages, args.dpi)
    ocr_pages(pages, use_gpu=args.gpu, engine=args.engine)
    scan_pages(pages)
    build_review()


if __name__ == "__main__":
    main()
