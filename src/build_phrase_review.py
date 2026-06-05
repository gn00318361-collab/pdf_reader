from __future__ import annotations

import argparse
import html
from pathlib import Path

from pipeline_common import REVIEW_DIR, ensure_dirs, read_json


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build_phrase_review() -> Path:
    ensure_dirs()
    path = REVIEW_DIR / "phrase_occurrences.json"
    occurrences = read_json(path) if path.exists() else []

    rows = []
    for item in occurrences:
        crop = item.get("phrase_crop_image") or ""
        crop_name = Path(crop).name if crop else ""
        crop_src = f"phrase_crops/{esc(crop_name)}" if crop_name else ""
        image = item.get("annotated_image") or ""
        image_name = Path(image).name if image else ""
        image_link = f"../pages/{esc(image_name)}" if image_name else ""
        thumbnail = (
            f"<img class=\"thumb\" src=\"{crop_src}\" loading=\"lazy\" alt=\"phrase crop\">"
            if crop_src
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('page'))}</td>"
            f"<td>{esc(item.get('token_id'))}</td>"
            f"<td class=\"thumb-cell\">{thumbnail}</td>"
            f"<td class=\"phrase\">{esc(item.get('candidate_phrase'))}</td>"
            f"<td>{esc(item.get('char'))}</td>"
            f"<td>{esc(' / '.join(item.get('readings') or []))}</td>"
            f"<td>{esc(item.get('context'))}</td>"
            f"<td>{esc(item.get('region_text'))}</td>"
            f"<td><a href=\"{image_link}\">annotated</a></td>"
            "</tr>"
        )

    body = "\n".join(rows) or "<tr><td colspan=\"9\">目前沒有詞級候選。</td></tr>"
    output = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>詞級多音字候選</title>
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
      --input-bg: #ffffff;
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
      --input-bg: #151a20;
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
      padding: 24px 32px 16px;
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
    .controls {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .theme-toggle, input {{
      border: 1px solid var(--border);
      background: var(--button-bg);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 14px;
    }}
    .theme-toggle {{
      cursor: pointer;
      white-space: nowrap;
    }}
    .theme-toggle:hover {{
      background: var(--button-hover);
    }}
    input {{
      background: var(--input-bg);
      min-width: 220px;
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
    .thumb-cell {{
      width: 300px;
    }}
    .thumb {{
      display: block;
      width: min(300px, 30vw);
      max-width: 100%;
      height: auto;
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 4px;
    }}
    .phrase {{
      font-size: 18px;
      font-weight: 700;
      white-space: nowrap;
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
        width: 260px;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>詞級多音字候選</h1>
      <div class="summary">候選數量：<span id="visibleCount">{len(occurrences)}</span> / {len(occurrences)}</div>
    </div>
    <div class="controls">
      <input id="filterBox" type="search" placeholder="篩選字、短語、頁碼、OCR 文字">
      <button class="theme-toggle" type="button" id="themeToggle">切換深色</button>
    </div>
  </header>
  <main>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>頁碼</th>
            <th>區塊 ID</th>
            <th>詞級截圖</th>
            <th>候選短語</th>
            <th>多音字</th>
            <th>可能讀音</th>
            <th>上下文</th>
            <th>OCR region</th>
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
    const savedTheme = localStorage.getItem("phrase-review-theme");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

    function applyTheme(theme) {{
      root.dataset.theme = theme;
      button.textContent = theme === "dark" ? "切換淺色" : "切換深色";
      localStorage.setItem("phrase-review-theme", theme);
    }}

    applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
    button.addEventListener("click", () => {{
      applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
    }});

    const filterBox = document.getElementById("filterBox");
    const visibleCount = document.getElementById("visibleCount");
    const rows = Array.from(document.querySelectorAll("tbody tr"));
    filterBox.addEventListener("input", () => {{
      const q = filterBox.value.trim().toLowerCase();
      let shown = 0;
      for (const row of rows) {{
        const match = !q || row.textContent.toLowerCase().includes(q);
        row.style.display = match ? "" : "none";
        if (match) shown += 1;
      }}
      visibleCount.textContent = shown;
    }});
  </script>
</body>
</html>
"""
    out_path = REVIEW_DIR / "phrase_review.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote phrase review HTML -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static phrase-level polyphonic candidate dashboard.")
    parser.parse_args()
    build_phrase_review()


if __name__ == "__main__":
    main()

