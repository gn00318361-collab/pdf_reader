from __future__ import annotations

import argparse
import html
import shutil
from pathlib import Path

from pipeline_common import REVIEW_DIR, ensure_dirs, read_json


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def build_review_dashboard() -> Path:
    ensure_dirs()
    semantic_path = REVIEW_DIR / "semantic_review_candidates.json"
    scored_path = REVIEW_DIR / "scored_phrase_candidates.json"
    path = semantic_path if semantic_path.exists() else scored_path
    candidates = read_json(path) if path.exists() else []

    rows = []
    for index, item in enumerate(candidates):
        crop = item.get("phrase_crop_image") or ""
        crop_name = Path(crop).name if crop else ""
        crop_src = f"phrase_crops/{esc(crop_name)}" if crop_name else ""
        image = item.get("annotated_image") or item.get("annotated_page_path") or ""
        image_name = Path(image).name if image else ""
        image_link = f"../pages/{esc(image_name)}" if image_name else ""
        thumbnail = f"<img class=\"thumb\" src=\"{crop_src}\" loading=\"lazy\" alt=\"phrase crop\">" if crop_src else ""
        status = item.get("status")
        priority = item.get("priority")
        token_id = item.get("token_id") or item.get("region_id")
        candidate_phrase = item.get("candidate_phrase") or item.get("matched_phrase") or item.get("context_window_4")
        matched_pattern = item.get("matched_pattern") or item.get("matched_phrase") or ""
        classifier_status = item.get("classifier_status") or item.get("status") or ""
        review_id = item.get("char_occurrence_id") or "|".join(
            str(value)
            for value in [
                item.get("page", ""),
                token_id or "",
                item.get("char", ""),
                item.get("char_index", item.get("char_index_in_region", "")),
                candidate_phrase or "",
            ]
        )
        rows.append(
            f"<tr data-status=\"{esc(status)}\" data-priority=\"{esc(priority)}\" "
            f"data-review-id=\"{esc(review_id)}\" data-order=\"{index}\">"
            f"<td class=\"check-cell\"><input class=\"row-check\" type=\"checkbox\" aria-label=\"標記已檢查\"></td>"
            f"<td class=\"check-cell\"><input class=\"issue-check\" type=\"checkbox\" aria-label=\"標記有錯或需修正\"></td>"
            f"<td><span class=\"pill {esc(priority)}\">{esc(priority)}</span></td>"
            f"<td>{esc(status)}</td>"
            f"<td>{esc(item.get('page'))}</td>"
            f"<td>{esc(token_id)}</td>"
            f"<td class=\"thumb-cell\">{thumbnail}</td>"
            f"<td class=\"phrase\">{esc(candidate_phrase)}</td>"
            f"<td>{esc(item.get('char'))}</td>"
            f"<td class=\"bpmf\">{esc(item.get('expected_bopomofo') or '待判斷')}</td>"
            f"<td>{esc(matched_pattern)}</td>"
            f"<td>{esc(classifier_status)}</td>"
            f"<td class=\"reason-cell\">{esc(item.get('reason'))}</td>"
            f"<td class=\"region-cell\">{esc(item.get('region_text'))}</td>"
            f"<td><a href=\"{image_link}\" target=\"_blank\" rel=\"noopener noreferrer\">annotated</a></td>"
            "</tr>"
        )

    body = "\n".join(rows) or "<tr><td colspan=\"15\">目前沒有候選。</td></tr>"
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
      --issue-bg: #fff1f2;
      --issue-border: #e11d48;
      --issue-text: #be123c;
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
      --issue-bg: #351820;
      --issue-border: #fb7185;
      --issue-text: #fda4af;
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
    .theme-toggle, .page-button, .state-button, input:not([type="checkbox"]), select {{
      border: 1px solid var(--border);
      background: var(--button-bg);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 14px;
    }}
    .theme-toggle, .page-button, .state-button {{
      cursor: pointer;
      white-space: nowrap;
    }}
    .theme-toggle:hover, .page-button:hover:not(:disabled), .state-button:hover {{
      background: var(--button-hover);
    }}
    .page-button:disabled {{
      cursor: not-allowed;
      opacity: 0.45;
    }}
    input:not([type="checkbox"]) {{
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
      table-layout: fixed;
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
      width: 340px;
      min-width: 320px;
    }}
    .check-cell {{
      width: 28px;
      min-width: 28px;
      max-width: 28px;
      text-align: center;
      padding-left: 4px;
      padding-right: 4px;
    }}
    .row-check, .issue-check {{
      width: 16px;
      height: 16px;
      accent-color: var(--link);
      cursor: pointer;
    }}
    .issue-check {{
      accent-color: var(--issue-border);
    }}
    .checked-row {{
      opacity: 0.55;
      background: var(--panel-2);
    }}
    .checked-row .phrase,
    .checked-row .bpmf {{
      color: var(--muted);
    }}
    .issue-row {{
      background: var(--issue-bg);
      box-shadow: inset 4px 0 0 var(--issue-border);
    }}
    .issue-row .phrase,
    .issue-row .bpmf {{
      color: var(--issue-text);
    }}
    .empty-row td {{
      color: var(--muted);
      text-align: center;
      padding: 18px 12px;
    }}
    .thumb {{
      display: block;
      width: 320px;
      max-width: 320px;
      height: auto;
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 4px;
    }}
    .phrase {{
      font-size: 18px;
      font-weight: 700;
      white-space: normal;
      word-break: keep-all;
      line-height: 1.35;
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
    .priority-col {{ width: 88px; }}
    .status-col {{ width: 138px; }}
    .page-col {{ width: 44px; }}
    .token-col {{ width: 64px; }}
    .phrase-col {{ width: 160px; }}
    .char-col {{ width: 58px; }}
    .bpmf-col {{ width: 92px; }}
    .rule-col {{ width: 92px; }}
    .classifier-col {{ width: 138px; }}
    .reason-col {{ width: 260px; }}
    .region-col {{ width: 300px; }}
    .link-col {{ width: 82px; }}
    .reason-cell,
    .region-cell {{
      line-height: 1.45;
      word-break: break-word;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>詞級候選判讀清單</h1>
      <div class="summary">
        <span>待審顯示：<span id="visibleCount">{len(candidates)}</span> / <span id="pendingCount">{len(candidates)}</span></span>
        <span>已檢查 OK：<span id="checkedCount">0</span></span>
        <span>有錯/需修正：<span id="issueCount">0</span></span>
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
        <option value="semantic_classified">semantic_classified</option>
        <option value="semantic_unresolved">semantic_unresolved</option>
        <option value="unresolved">unresolved</option>
      </select>
      <button class="theme-toggle" type="button" id="themeToggle">切換深色</button>
      <button class="state-button" type="button" id="exportState">匯出標記</button>
      <label class="state-button" for="importState">匯入標記</label>
      <input id="importState" type="file" accept="application/json,.json" hidden>
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
            <th class="check-cell" title="已檢查">✓</th>
            <th class="check-cell" title="有錯/需修正">!</th>
            <th class="priority-col">優先級</th>
            <th class="status-col">狀態</th>
            <th class="page-col">頁碼</th>
            <th class="token-col">區塊 ID</th>
            <th class="thumb-cell">詞級截圖</th>
            <th class="phrase-col">候選短語</th>
            <th class="char-col">多音字</th>
            <th class="bpmf-col">推估注音</th>
            <th class="rule-col">規則</th>
            <th class="classifier-col">分類狀態</th>
            <th class="reason-col">原因</th>
            <th class="region-col">OCR region</th>
            <th class="link-col">標記圖</th>
          </tr>
        </thead>
        <tbody id="pendingBody">{body}</tbody>
      </table>
      </div>
    </section>
    <section class="review-section">
      <div class="section-title">
        <h2>Issues</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="check-cell" title="已檢查">✓</th>
              <th class="check-cell" title="有錯/需修正">!</th>
              <th class="priority-col">優先級</th>
              <th class="status-col">狀態</th>
              <th class="page-col">頁碼</th>
              <th class="token-col">區塊 ID</th>
              <th class="thumb-cell">詞級截圖</th>
              <th class="phrase-col">候選短語</th>
              <th class="char-col">多音字</th>
              <th class="bpmf-col">推估注音</th>
              <th class="rule-col">規則</th>
              <th class="classifier-col">分類狀態</th>
              <th class="reason-col">原因</th>
              <th class="region-col">OCR region</th>
              <th class="link-col">標記圖</th>
            </tr>
          </thead>
          <tbody id="issueBody">
            <tr class="empty-row" id="issueEmpty"><td colspan="15">尚未標記任何錯誤。</td></tr>
          </tbody>
        </table>
      </div>
    </section>
    <section class="review-section">
      <div class="section-title">
        <h2>Checked / OK</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th class="check-cell" title="已檢查">✓</th>
              <th class="check-cell" title="有錯/需修正">!</th>
              <th class="priority-col">優先級</th>
              <th class="status-col">狀態</th>
              <th class="page-col">頁碼</th>
              <th class="token-col">區塊 ID</th>
              <th class="thumb-cell">詞級截圖</th>
              <th class="phrase-col">候選短語</th>
              <th class="char-col">多音字</th>
              <th class="bpmf-col">推估注音</th>
              <th class="rule-col">規則</th>
              <th class="classifier-col">分類狀態</th>
              <th class="reason-col">原因</th>
              <th class="region-col">OCR region</th>
              <th class="link-col">標記圖</th>
            </tr>
          </thead>
          <tbody id="checkedBody">
            <tr class="empty-row" id="checkedEmpty"><td colspan="15">尚未勾選任何項目。</td></tr>
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
    const issueCount = document.getElementById("issueCount");
    const pendingBody = document.getElementById("pendingBody");
    const issueBody = document.getElementById("issueBody");
    const checkedBody = document.getElementById("checkedBody");
    const issueEmpty = document.getElementById("issueEmpty");
    const checkedEmpty = document.getElementById("checkedEmpty");
    const storageKey = "scored-review-checked-ids";
    const issueStorageKey = "scored-review-issue-ids";
    const rows = Array.from(document.querySelectorAll("#pendingBody tr[data-review-id]"));
    const checkedIds = new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"));
    const issueIds = new Set(JSON.parse(localStorage.getItem(issueStorageKey) || "[]"));
    let currentPage = 1;

    function saveChecked() {{
      localStorage.setItem(storageKey, JSON.stringify(Array.from(checkedIds)));
    }}

    function saveIssues() {{
      localStorage.setItem(issueStorageKey, JSON.stringify(Array.from(issueIds)));
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
      const issueRows = Array.from(issueBody.querySelectorAll("tr[data-review-id]"));
      pendingCount.textContent = pendingRows.length;
      checkedCount.textContent = checkedRows.length;
      issueCount.textContent = issueRows.length;
      checkedEmpty.style.display = checkedRows.length ? "none" : "";
      issueEmpty.style.display = issueRows.length ? "none" : "";
    }}

    function setRowChecked(row, checked) {{
      const checkbox = row.querySelector(".row-check");
      checkbox.checked = checked;
      row.classList.toggle("checked-row", checked && !issueIds.has(row.dataset.reviewId));
      if (checked) {{
        checkedIds.add(row.dataset.reviewId);
        if (!issueIds.has(row.dataset.reviewId)) {{
          checkedBody.appendChild(row);
          sortRows(checkedBody);
        }}
      }} else {{
        checkedIds.delete(row.dataset.reviewId);
        if (!issueIds.has(row.dataset.reviewId)) {{
          pendingBody.appendChild(row);
          sortRows(pendingBody);
        }}
      }}
      saveChecked();
      updateCounts();
      applyFilters();
    }}

    function setRowIssue(row, issue) {{
      const issueCheckbox = row.querySelector(".issue-check");
      const reviewCheckbox = row.querySelector(".row-check");
      issueCheckbox.checked = issue;
      row.classList.toggle("issue-row", issue);
      row.classList.toggle("checked-row", !issue && checkedIds.has(row.dataset.reviewId));
      if (issue) {{
        issueIds.add(row.dataset.reviewId);
        checkedIds.add(row.dataset.reviewId);
        reviewCheckbox.checked = true;
        issueBody.appendChild(row);
        sortRows(issueBody);
      }} else {{
        issueIds.delete(row.dataset.reviewId);
        if (checkedIds.has(row.dataset.reviewId)) {{
          checkedBody.appendChild(row);
          sortRows(checkedBody);
        }} else {{
          pendingBody.appendChild(row);
          sortRows(pendingBody);
        }}
      }}
      saveChecked();
      saveIssues();
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
      const issueCheckbox = row.querySelector(".issue-check");
      checkbox.addEventListener("change", () => setRowChecked(row, checkbox.checked));
      issueCheckbox.addEventListener("change", () => setRowIssue(row, issueCheckbox.checked));
      if (issueIds.has(row.dataset.reviewId)) {{
        issueCheckbox.checked = true;
        checkbox.checked = true;
        row.classList.add("issue-row");
        issueBody.appendChild(row);
      }} else if (checkedIds.has(row.dataset.reviewId)) {{
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
    function rowPayload(row) {{
      const cells = Array.from(row.querySelectorAll("td")).map(cell => cell.textContent.trim());
      return {{
        id: row.dataset.reviewId,
        priority: row.dataset.priority,
        status: row.dataset.status,
        page: cells[4],
        region_id: cells[5],
        candidate_phrase: cells[7],
        char: cells[8],
        expected_bopomofo: cells[9],
        matched_pattern: cells[10],
        classifier_status: cells[11],
        reason: cells[12],
        region_text: cells[13],
      }};
    }}

    function exportReviewState() {{
      const allRows = Array.from(document.querySelectorAll("tr[data-review-id]"));
      const payload = {{
        schema: "pdf_reader_review_state.v1",
        exported_at: new Date().toISOString(),
        source: "scored_review.html",
        reviewed_ids: Array.from(checkedIds),
        issue_ids: Array.from(issueIds),
        issues: allRows.filter(row => issueIds.has(row.dataset.reviewId)).map(rowPayload),
      }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: "application/json" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "review_state.json";
      link.click();
      URL.revokeObjectURL(url);
    }}

    function importReviewState(file) {{
      const reader = new FileReader();
      reader.onload = () => {{
        const payload = JSON.parse(String(reader.result || "{{}}"));
        checkedIds.clear();
        issueIds.clear();
        for (const id of payload.reviewed_ids || []) checkedIds.add(id);
        for (const id of payload.issue_ids || []) issueIds.add(id);
        for (const row of rows) {{
          row.classList.remove("checked-row", "issue-row");
          row.querySelector(".row-check").checked = false;
          row.querySelector(".issue-check").checked = false;
          pendingBody.appendChild(row);
        }}
        for (const row of rows) {{
          if (issueIds.has(row.dataset.reviewId)) {{
            row.querySelector(".issue-check").checked = true;
            row.querySelector(".row-check").checked = true;
            row.classList.add("issue-row");
            issueBody.appendChild(row);
          }} else if (checkedIds.has(row.dataset.reviewId)) {{
            row.querySelector(".row-check").checked = true;
            row.classList.add("checked-row");
            checkedBody.appendChild(row);
          }}
        }}
        sortRows(pendingBody);
        sortRows(issueBody);
        sortRows(checkedBody);
        saveChecked();
        saveIssues();
        updateCounts();
        resetToFirstPage();
      }};
      reader.readAsText(file);
    }}

    document.getElementById("exportState").addEventListener("click", exportReviewState);
    document.getElementById("importState").addEventListener("change", event => {{
      const file = event.target.files && event.target.files[0];
      if (file) importReviewState(file);
      event.target.value = "";
    }});
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
    out_path = REVIEW_DIR / "review_dashboard.html"
    out_path.write_text(output, encoding="utf-8")
    shutil.copyfile(out_path, REVIEW_DIR / "index.html")
    shutil.copyfile(out_path, REVIEW_DIR / "scored_review.html")
    print(f"wrote review dashboard HTML -> {out_path}")
    print(f"wrote review dashboard index -> {REVIEW_DIR / 'index.html'}")
    print(f"wrote legacy scored review HTML -> {REVIEW_DIR / 'scored_review.html'}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the main review dashboard.")
    parser.parse_args()
    build_review_dashboard()


if __name__ == "__main__":
    main()
