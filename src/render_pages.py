from __future__ import annotations

import argparse

import fitz

from pipeline_common import RAW_PDF, ensure_dirs, page_image_path, parse_pages


def render_pages(pages: list[int], dpi: int) -> list[str]:
    ensure_dirs()
    written: list[str] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(RAW_PDF) as doc:
        page_count = len(doc)
        for page_number in pages:
            if page_number < 1 or page_number > page_count:
                raise ValueError(f"Page {page_number} is outside PDF page range 1-{page_count}.")
            page = doc.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = page_image_path(page_number)
            pixmap.save(out_path)
            written.append(str(out_path))
            print(f"rendered page {page_number} -> {out_path}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Render selected PDF pages to PNG.")
    parser.add_argument("--pages", default="22", help="Comma/range page list, e.g. 1,4,16-27.")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    render_pages(parse_pages(args.pages), args.dpi)


if __name__ == "__main__":
    main()

