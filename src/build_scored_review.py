from __future__ import annotations

import argparse
import html
from pathlib import Path

from pipeline_common import REVIEW_DIR, ensure_dirs, read_json


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build_scored_review() -> Path:
    ensure_dirs()
    path = REVIEW_DIR / "scored_phrase_candidates.json"
    candidates = read_json(path) if path.exists() else []

    rows = []
    for index, item in enumerate(candidates):
        crop = item.get("phrase_crop_image") or ""
        crop_name = Path(crop).name if crop else ""
        crop_src = f"phrase_crops/{esc(crop_name)}" if crop_name else ""
        image = item.get("annotated_image") or ""
        image_name = Path(image).name if image else ""
        image_link = f"../pages/{esc(image_name)}" if image_name else ""
        thumbnail = f"<img class=\"thumb\" src=\"{crop_src}\" loading=\"lazy\" alt=\"phrase crop\">" if crop_src else ""
        status = item.get("status")
        priority = item.get("priority")
        review_id = "|".join(
            str(item.get(key, ""))
            for key in ["page", "token_id", "char", "char_index", "candidate_phrase"]
        )
        rows.append(
            f"<tr data-status=\"{esc(status)}\" data-priority=\"{esc(priority)}\" "
            f"data-review-id=\"{esc(review_id)}\" data-order=\"{index}\">"
            f"<td class=\"check-cell\"><input class=\"row-check\" type=\"checkbox\" aria-label=\"標記已檢查\"></td>"
            f"<td><span class=\"pill {esc(priority)}\">{esc(priority)}</span></td>"
            f"<td>{esc(status)}</td>"
            f"<td>{esc(item.get('page'))}</td>"
            f"<td>{esc(item.get('token_id'))}</td>"
            f"<td class=\"thumb-cell\">{thumbnail}</td>"
            f"<td class=\"phrase\">{esc(item.get('candidate_phrase'))}</td>"
            f"<td>{esc(item.get('char'))}</td>"
            f"<td class=\"bpmf\">{esc(item.get('expected_bopomofo') or '待判斷')}</td>"
            f"<td>{esc(item.get('matched_pattern') or '')}</td>"
            f"<td>{esc(item.get('reason'))}</td>"
            f"<td>{esc(item.get('region_text'))}</td>"
            f"<td><a href=\"{image_link}\" target=\"_blank\" rel=\"noopener noreferrer\">annotated</a></td>"
            "</tr>"
        )

    body = "\n".join(rows) or "<tr><td colspan=\"13\">目前沒有候選。</td></tr>"
    output = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>詞級候選判讀清單</title>
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
      --high: #c2410c;
      --medium: #a16207;
      --low: #166534;
      --unresolved: #475569;
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
      --high: #fb923c;
      --medium: #facc15;
      --low: #86efac;
      --unresolved: #cbd5e1;
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
    .summary span + span {{
      margin-left: 12px;
    }}
    .controls {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .theme-toggle, .page-button, input, select {{
      border: 1px solid var(--border);
      background: var(--button-bg);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 14px;
    }}
    .theme-toggle, .page-button {{
      cursor: pointer;
      white-space: nowrap;
    }}
    .theme-toggle:hover, .page-button:hover:not(:disabled) {{
      background: var(--button-hover);
    }}
    .page-button:disabled {{
      cursor: not-allowed;
      opacity: 0.45;
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
    }}
    .review-section + .review-section {{
      margin-top: 28px;
    }}
    .section-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 10px;
    }}
    .section-title h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .pager {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 14px;
    }}
    .page-size-label {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }}
    .pager select {{
      padding: 6px 8px;
    }}
    .page-info {{
      min-width: 78px;
      text-align: center;
      color: var(--text);
      font-variant-numeric: tabular-nums;
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
    .check-cell {{
      width: 44px;
      text-align: center;
    }}
    .row-check {{
      width: 18px;
      height: 18px;
      accent-color: var(--link);
      cursor: pointer;
    }}
    .checked-row {{
      opacity: 0.55;
      background: var(--panel-2);
    }}
    .checked-row .phrase,
    .checked-row .bpmf {{
      color: var(--muted);
    }}
    .empty-row td {{
      color: var(--muted);
      text-align: center;
      padding: 18px 12px;
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
    .bpmf {{
      font-size: 18px;
      white-space: nowrap;
    }}
    .pill {{
      display: inline-block;
      min-width: 74px;
      padding: 3px 7px;
      border-radius: 999px;
      text-align: center;
      font-weight: 700;
      border: 1px solid currentColor;
    }}
    .high {{ color: var(--high); }}
    .medium {{ color: var(--medium); }}
    .low {{ color: var(--low); }}
    .unresolved {{ color: var(--unresolved); }}
    a {{ color: var(--link); }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>詞級候選判讀清單</h1>
      <div class="summary">
        <span>待審顯示：<span id="visibleCount">{len(candidates)}</span> / <span id="pendingCount">{len(candidates)}</span></span>
        <span>已檢查：<span id="checkedCount">0</span></span>
      </div>
    </div>
    <div class="controls">
      <input id="filterBox" type="search" placeholder="篩選字、短語、頁碼、OCR 文字">
      <select id="priorityFilter">
        <option value="">全部優先級</option>
        <option value="high">high</option>
        <option value="medium">medium</option>
        <option value="low">low</option>
        <option value="unresolved">unresolved</option>
      </select>
      <select id="statusFilter">
        <option value="">全部狀態</option>
        <option value="rule_matched">rule_matched</option>
        <option value="unresolved">unresolved</option>
      </select>
      <button class="theme-toggle" type="button" id="themeToggle">切換深色</button>
    </div>
  </header>
  <main>
    <section class="review-section">
      <div class="section-title">
        <h2>待審候選</h2>
        <div class="pager" aria-label="待審候選分頁">
          <label class="page-size-label" for="pageSizeSelect">
            每頁
            <select id="pageSizeSelect">
              <option value="25">25</option>
              <option value="50" selected>50</option>
              <option value="100">100</option>
              <option value="all">全部</option>
            </select>
          </label>
          <button class="page-button" type="button" id="prevPage">上一頁</button>
          <span class="page-info" id="pageInfo">1 / 1</span>
          <button class="page-button" type="button" id="nextPage">下一頁</button>
        </div>
      </div>
      <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>檢查</th>
            <th>優先級</th>
            <th>狀態</th>
            <th>頁碼</th>
            <th>區塊 ID</th>
            <th>詞級截圖</th>
            <th>候選短語</th>
            <th>多音字</th>
            <th>推估注音</th>
            <th>規則</th>
            <th>原因</th>
            <th>OCR region</th>
            <th>標記圖</th>
          </tr>
        </thead>
        <tbody id="pendingBody">{body}</tbody>
      </table>
      </div>
    </section>
    <section class="review-section">
      <div class="section-title">
        <h2>Checked</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>檢查</th>
              <th>優先級</th>
              <th>狀態</th>
              <th>頁碼</th>
              <th>區塊 ID</th>
              <th>詞級截圖</th>
              <th>候選短語</th>
              <th>多音字</th>
              <th>推估注音</th>
              <th>規則</th>
              <th>原因</th>
              <th>OCR region</th>
              <th>標記圖</th>
            </tr>
          </thead>
          <tbody id="checkedBody">
            <tr class="empty-row" id="checkedEmpty"><td colspan="13">尚未勾選任何項目。</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const root = document.documentElement;
    const button = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("scored-review-theme");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    function applyTheme(theme) {{
      root.dataset.theme = theme;
      button.textContent = theme === "dark" ? "切換淺色" : "切換深色";
      localStorage.setItem("scored-review-theme", theme);
    }}
    applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
    button.addEventListener("click", () => applyTheme(root.dataset.theme === "dark" ? "light" : "dark"));

    const filterBox = document.getElementById("filterBox");
    const priorityFilter = document.getElementById("priorityFilter");
    const statusFilter = document.getElementById("statusFilter");
    const pageSizeSelect = document.getElementById("pageSizeSelect");
    const prevPage = document.getElementById("prevPage");
    const nextPage = document.getElementById("nextPage");
    const pageInfo = document.getElementById("pageInfo");
    const visibleCount = document.getElementById("visibleCount");
    const pendingCount = document.getElementById("pendingCount");
    const checkedCount = document.getElementById("checkedCount");
    const pendingBody = document.getElementById("pendingBody");
    const checkedBody = document.getElementById("checkedBody");
    const checkedEmpty = document.getElementById("checkedEmpty");
    const storageKey = "scored-review-checked-ids";
    const rows = Array.from(document.querySelectorAll("#pendingBody tr[data-review-id]"));
    const checkedIds = new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"));
    let currentPage = 1;

    function saveChecked() {{
      localStorage.setItem(storageKey, JSON.stringify(Array.from(checkedIds)));
    }}

    function sortRows(tbody) {{
      const sorted = Array.from(tbody.querySelectorAll("tr[data-review-id]")).sort(
        (a, b) => Number(a.dataset.order) - Number(b.dataset.order)
      );
      for (const row of sorted) tbody.appendChild(row);
    }}

    function updateCounts() {{
      const pendingRows = Array.from(pendingBody.querySelectorAll("tr[data-review-id]"));
      const checkedRows = Array.from(checkedBody.querySelectorAll("tr[data-review-id]"));
      pendingCount.textContent = pendingRows.length;
      checkedCount.textContent = checkedRows.length;
      checkedEmpty.style.display = checkedRows.length ? "none" : "";
    }}

    function setRowChecked(row, checked) {{
      const checkbox = row.querySelector(".row-check");
      checkbox.checked = checked;
      row.classList.toggle("checked-row", checked);
      if (checked) {{
        checkedIds.add(row.dataset.reviewId);
        checkedBody.appendChild(row);
        sortRows(checkedBody);
      }} else {{
        checkedIds.delete(row.dataset.reviewId);
        pendingBody.appendChild(row);
        sortRows(pendingBody);
      }}
      saveChecked();
      updateCounts();
      applyFilters();
    }}

    function getPageSize() {{
      const value = pageSizeSelect.value;
      return value === "all" ? Infinity : Number(value);
    }}

    function rowMatchesFilters(row) {{
      const q = filterBox.value.trim().toLowerCase();
      const priority = priorityFilter.value;
      const status = statusFilter.value;
      const textMatch = !q || row.textContent.toLowerCase().includes(q);
      const priorityMatch = !priority || row.dataset.priority === priority;
      const statusMatch = !status || row.dataset.status === status;
      return textMatch && priorityMatch && statusMatch;
    }}

    function resetToFirstPage() {{
      currentPage = 1;
      applyFilters();
    }}

    for (const row of rows) {{
      const checkbox = row.querySelector(".row-check");
      checkbox.addEventListener("change", () => setRowChecked(row, checkbox.checked));
      if (checkedIds.has(row.dataset.reviewId)) {{
        checkbox.checked = true;
        row.classList.add("checked-row");
        checkedBody.appendChild(row);
      }}
    }}

    function applyFilters() {{
      const pendingRows = Array.from(pendingBody.querySelectorAll("tr[data-review-id]"));
      const matchedRows = pendingRows.filter(rowMatchesFilters);
      const pageSize = getPageSize();
      const totalPages = pageSize === Infinity ? 1 : Math.max(1, Math.ceil(matchedRows.length / pageSize));
      currentPage = Math.min(Math.max(currentPage, 1), totalPages);
      const start = pageSize === Infinity ? 0 : (currentPage - 1) * pageSize;
      const end = pageSize === Infinity ? matchedRows.length : start + pageSize;
      const visibleRows = new Set(matchedRows.slice(start, end));

      for (const row of pendingRows) {{
        row.style.display = visibleRows.has(row) ? "" : "none";
      }}
      visibleCount.textContent = matchedRows.length;
      pageInfo.textContent = `${{currentPage}} / ${{totalPages}}`;
      prevPage.disabled = currentPage <= 1;
      nextPage.disabled = currentPage >= totalPages;
    }}
    sortRows(pendingBody);
    sortRows(checkedBody);
    updateCounts();
    applyFilters();
    filterBox.addEventListener("input", resetToFirstPage);
    priorityFilter.addEventListener("change", resetToFirstPage);
    statusFilter.addEventListener("change", resetToFirstPage);
    pageSizeSelect.addEventListener("change", resetToFirstPage);
    prevPage.addEventListener("click", () => {{
      currentPage -= 1;
      applyFilters();
    }});
    nextPage.addEventListener("click", () => {{
      currentPage += 1;
      applyFilters();
    }});
  </script>
</body>
</html>
"""
    out_path = REVIEW_DIR / "scored_review.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote scored review HTML -> {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build scored phrase candidate dashboard.")
    parser.parse_args()
    build_scored_review()


if __name__ == "__main__":
    main()
