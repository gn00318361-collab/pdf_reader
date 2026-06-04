#!/usr/bin/env python3
import argparse
import json
import re
import ssl
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import fitz


ZHUYIN_RE = re.compile(r"[ㄅ-ㄩˊˇˋ˙]")
MOE_SEARCH_URL = "https://dict.revised.moe.edu.tw/search.jsp?md=1&word={word}"


def inspect_pdf(path: Path, page_number: int | None = None) -> list[dict]:
    doc = fitz.open(path)
    page_indexes = [page_number - 1] if page_number else range(doc.page_count)
    rows = []

    for page_index in page_indexes:
        page = doc[page_index]
        text = page.get_text()
        rows.append(
            {
                "page": page_index + 1,
                "text_chars": len(text.strip()),
                "zhuyin_chars": len(ZHUYIN_RE.findall(text)),
                "images": len(page.get_images(full=True)),
                "fonts": len(page.get_fonts()),
                "is_extractable_text": bool(text.strip()),
            }
        )

    return rows


def render_page(path: Path, page_number: int, output: Path, scale: float = 2.0) -> Path:
    doc = fitz.open(path)
    page = doc[page_number - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    pix.save(output)
    return output


def lookup_moe_zhuyin(word: str) -> dict:
    url = MOE_SEARCH_URL.format(word=quote(word))
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 pdf-zhuyin-audit/0.1",
        },
    )
    ssl_fallback = False
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        ssl_fallback = True
        context = ssl._create_unverified_context()
        with urlopen(request, timeout=20, context=context) as response:
            html = response.read().decode("utf-8", errors="replace")

    description_match = re.search(
        r'<meta\s+name="Description"\s+content="([^"]+)"', html
    )
    description = description_match.group(1) if description_match else ""
    zhuyin_match = re.search(r"注音:([^,，]+)", description)
    zhuyin = zhuyin_match.group(1).strip().replace("\u3000", " ") if zhuyin_match else ""

    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""

    return {
        "word": word,
        "zhuyin": zhuyin,
        "source_url": url,
        "title": title,
        "description": description,
        "ssl_fallback": ssl_fallback,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect PDFs for extractable text and query MOE zhuyin."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("pdf", type=Path)
    inspect_parser.add_argument("--page", type=int)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("pdf", type=Path)
    render_parser.add_argument("--page", type=int, required=True)
    render_parser.add_argument("--output", type=Path, required=True)
    render_parser.add_argument("--scale", type=float, default=2.0)

    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("word")

    args = parser.parse_args()

    if args.command == "inspect":
        print(json.dumps(inspect_pdf(args.pdf, args.page), ensure_ascii=False, indent=2))
        return 0

    if args.command == "render":
        output = render_page(args.pdf, args.page, args.output, args.scale)
        print(output)
        return 0

    if args.command == "lookup":
        print(json.dumps(lookup_moe_zhuyin(args.word), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
