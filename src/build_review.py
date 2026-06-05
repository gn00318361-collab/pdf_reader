from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from pipeline_common import CROPS_DIR, PAGES_DIR, REVIEW_DIR, ensure_dirs, read_json, write_json


def html_escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def safe_name(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", text).strip("_") or "candidate"


def candidate_crop_name(candidate: dict[str, Any]) -> str:
    return (
        f"page_{int(candidate.get('page')):03d}_"
        f"{safe_name(candidate.get('token_id'))}_"
        f"{safe_name(candidate.get('matched_word'))}.webp"
    )


def expand_bbox(box: list[list[float]], image_size: tuple[int, int], pad_x: int = 80, pad_y: int = 36) -> tuple[int, int, int, int]:
    width, height = image_size
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    left = max(0, int(min(xs) - pad_x))
    top = max(0, int(min(ys) - pad_y))
    right = min(width, int(max(xs) + pad_x))
    bottom = min(height, int(max(ys) + pad_y))
    return left, top, right, bottom


def draw_candidate_highlight(crop: Image.Image, box: list[list[float]], crop_origin: tuple[int, int]) -> Image.Image:
    image = crop.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    ox, oy = crop_origin
    polygon = [(point[0] - ox, point[1] - oy) for point in box]
    draw.polygon(polygon, fill=(255, 106, 0, 55), outline=(230, 76, 0, 230))
    return Image.alpha_composite(image, overlay).convert("RGB")


def generate_candidate_crops(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    image_cache: dict[int, Image.Image] = {}
    for candidate in candidates:
        page = candidate.get("page")
        box = candidate.get("box") or []
        if not page or len(box) < 4:
            continue

        page_number = int(page)
        image = image_cache.get(page_number)
        if image is None:
            image_path = PAGES_DIR / f"page_{page_number:03d}.png"
            if not image_path.exists():
                continue
            image = Image.open(image_path).convert("RGB")
            image_cache[page_number] = image

        left, top, right, bottom = expand_bbox(box, image.size)
        if right <= left or bottom <= top:
            continue
        crop = image.crop((left, top, right, bottom))
        crop = draw_candidate_highlight(crop, box, (left, top))
        out_path = CROPS_DIR / candidate_crop_name(candidate)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(out_path, "WEBP", quality=82, method=6)
        candidate["crop_image"] = str(out_path)
    return candidates


def build_review() -> Path:
    ensure_dirs()
    candidates_path = REVIEW_DIR / "review_candidates.json"
    candidates = read_json(candidates_path) if candidates_path.exists() else []
    candidates = generate_candidate_crops(candidates)
    write_json(candidates_path, candidates)

    rows = []
    for candidate in candidates:
        image = candidate.get("annotated_image") or ""
        image_name = Path(image).name if image else ""
        image_link = f"../pages/{html_escape(image_name)}" if image_name else ""
        crop = candidate.get("crop_image") or ""
        crop_name = Path(crop).name if crop else ""
        crop_src = f"crops/{html_escape(crop_name)}" if crop_name else ""
        thumbnail = (
            f"<img class=\"thumb\" src=\"{crop_src}\" loading=\"lazy\" alt=\"candidate crop\">"
            if crop_src
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{html_escape(candidate.get('page'))}</td>"
            f"<td>{html_escape(candidate.get('token_id'))}</td>"
            f"<td class=\"thumb-cell\">{thumbnail}</td>"
            f"<td>{html_escape(candidate.get('matched_word'))}</td>"
            f"<td>{html_escape(candidate.get('target_char'))}</td>"
            f"<td class=\"bpmf\">{html_escape(candidate.get('expected_bopomofo'))}</td>"
            f"<td>{html_escape(candidate.get('rule_confidence'))}</td>"
            f"<td>{html_escape(candidate.get('reason'))}</td>"
            f"<td>{html_escape(candidate.get('ocr_context'))}</td>"
            f"<td><a href=\"{image_link}\">annotated</a></td>"
            "</tr>"
        )

    body = "\n".join(rows) or "<tr><td colspan=\"10\">目前沒有候選項目。</td></tr>"
    output = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>校刊注音破音字審稿清單</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --panel-2: #eef2f6;
      --text: #1f2933;
      --muted: #52616f;
      --border: #d9dee7;
      --row-border: #e5e9f0;
      --link: #0b62b4;
      --button-bg: #ffffff;
      --button-hover: #eef2f6;
      --shadow: rgba(15, 23, 42, 0.08);
    }}
    [data-theme="dark"] {{
      color-scheme: dark;
      --bg: #111418;
      --panel: #181d23;
      --panel-2: #232a32;
      --text: #e7edf4;
      --muted: #aab6c4;
      --border: #38424d;
      --row-border: #2d363f;
      --link: #80bfff;
      --button-bg: #232a32;
      --button-hover: #2d363f;
      --shadow: rgba(0, 0, 0, 0.28);
    }}
    body {{
      margin: 0;
      font-family: "Microsoft JhengHei", "Noto Sans TC", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 24px 32px 12px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      letter-spacing: 0;
    }}
    .summary {{
      color: var(--muted);
    }}
    .theme-toggle {{
      border: 1px solid var(--border);
      background: var(--button-bg);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      white-space: nowrap;
    }}
    .theme-toggle:hover {{
      background: var(--button-hover);
    }}
    main {{
      padding: 24px 32px 40px;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      background: var(--panel);
      box-shadow: 0 2px 8px var(--shadow);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--row-border);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: var(--panel-2);
      font-weight: 700;
      white-space: nowrap;
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    .bpmf {{
      font-size: 18px;
      white-space: nowrap;
    }}
    .thumb-cell {{
      width: 360px;
    }}
    .thumb {{
      display: block;
      width: min(360px, 36vw);
      max-width: 100%;
      height: auto;
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 4px;
    }}
    a {{
      color: var(--link);
    }}
    @media (max-width: 900px) {{
      header {{
        align-items: flex-start;
        flex-direction: column;
      }}
      main {{
        padding: 16px;
      }}
      .thumb {{
        width: 280px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>校刊注音破音字審稿清單</h1>
      <div class="summary">候選數量：{len(candidates)}</div>
    </div>
    <button class="theme-toggle" type="button" id="themeToggle">切換深色</button>
  </header>
  <main>
    <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>頁碼</th>
          <th>區塊 ID</th>
          <th>截圖</th>
          <th>風險詞</th>
          <th>檢查字</th>
          <th>正確注音</th>
          <th>規則信心</th>
          <th>原因</th>
          <th>OCR 上下文</th>
          <th>標記圖</th>
        </tr>
      </thead>
      <tbody>
        {body}
      </tbody>
    </table>
    </div>
  </main>
  <script>
    const root = document.documentElement;
    const button = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("review-theme");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

    function applyTheme(theme) {{
      root.dataset.theme = theme;
      button.textContent = theme === "dark" ? "切換淺色" : "切換深色";
      localStorage.setItem("review-theme", theme);
    }}

    applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
    button.addEventListener("click", () => {{
      applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
    }});
  </script>
</body>
</html>
"""
    out_path = REVIEW_DIR / "review.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote review HTML -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static review dashboard HTML.")
    parser.parse_args()
    build_review()


if __name__ == "__main__":
    main()
