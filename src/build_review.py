from __future__ import annotations

import argparse
import html
from pathlib import Path

from pipeline_common import REVIEW_DIR, ensure_dirs, read_json


def html_escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build_review() -> Path:
    ensure_dirs()
    candidates_path = REVIEW_DIR / "review_candidates.json"
    candidates = read_json(candidates_path) if candidates_path.exists() else []

    rows = []
    for candidate in candidates:
        image = candidate.get("annotated_image") or ""
        image_name = Path(image).name if image else ""
        image_link = f"../pages/{html_escape(image_name)}" if image_name else ""
        rows.append(
            "<tr>"
            f"<td>{html_escape(candidate.get('page'))}</td>"
            f"<td>{html_escape(candidate.get('token_id'))}</td>"
            f"<td>{html_escape(candidate.get('matched_word'))}</td>"
            f"<td>{html_escape(candidate.get('target_char'))}</td>"
            f"<td class=\"bpmf\">{html_escape(candidate.get('expected_bopomofo'))}</td>"
            f"<td>{html_escape(candidate.get('rule_confidence'))}</td>"
            f"<td>{html_escape(candidate.get('reason'))}</td>"
            f"<td>{html_escape(candidate.get('ocr_context'))}</td>"
            f"<td><a href=\"{image_link}\">annotated</a></td>"
            "</tr>"
        )

    body = "\n".join(rows) or "<tr><td colspan=\"9\">目前沒有候選項目。</td></tr>"
    output = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>校刊注音破音字審稿清單</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft JhengHei", "Noto Sans TC", Arial, sans-serif;
      background: #f6f7f9;
      color: #1f2933;
    }}
    header {{
      padding: 24px 32px 12px;
      background: #ffffff;
      border-bottom: 1px solid #d9dee7;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      letter-spacing: 0;
    }}
    main {{
      padding: 24px 32px 40px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #d9dee7;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e5e9f0;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #eef2f6;
      font-weight: 700;
      white-space: nowrap;
    }}
    .bpmf {{
      font-size: 18px;
      white-space: nowrap;
    }}
    a {{
      color: #0b62b4;
    }}
  </style>
</head>
<body>
  <header>
    <h1>校刊注音破音字審稿清單</h1>
    <div>候選數量：{len(candidates)}</div>
  </header>
  <main>
    <table>
      <thead>
        <tr>
          <th>頁碼</th>
          <th>區塊 ID</th>
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
  </main>
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

