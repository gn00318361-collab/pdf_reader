#!/usr/bin/env python3
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageOps


CSV_FIELDS = [
    "id",
    "page",
    "bbox",
    "crop_path",
    "overlay_path",
    "printed_zhuyin",
    "expected_zhuyin",
    "suspected_error",
    "crop_quality",
    "note",
]


@dataclass
class Box:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    def padded(self, padding: int, image_size: tuple[int, int]) -> "Box":
        width, height = image_size
        return Box(
            max(0, self.left - padding),
            max(0, self.top - padding),
            min(width, self.right + padding),
            min(height, self.bottom + padding),
        )

    def as_list(self) -> list[int]:
        return [self.left, self.top, self.right, self.bottom]


def render_pages(pdf_path: Path, pages_dir: Path, scale: float) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for index in range(doc.page_count):
        page_number = index + 1
        pix = doc[index].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        image_path = pages_dir / f"page_{page_number:03d}.png"
        pix.save(image_path)
        pages.append(
            {
                "page": page_number,
                "image_path": image_path,
                "width": pix.width,
                "height": pix.height,
            }
        )
    return pages


def dark_row_projection(image: Image.Image, threshold: int) -> list[int]:
    gray = ImageOps.grayscale(image)
    width, height = gray.size
    pixels = gray.load()
    rows = []
    for y in range(height):
        count = 0
        for x in range(width):
            if pixels[x, y] < threshold:
                count += 1
        rows.append(count)
    return rows


def dark_col_projection(image: Image.Image, threshold: int, top: int, bottom: int) -> list[int]:
    gray = ImageOps.grayscale(image)
    width, _ = gray.size
    pixels = gray.load()
    cols = []
    for x in range(width):
        count = 0
        for y in range(top, bottom):
            if pixels[x, y] < threshold:
                count += 1
        cols.append(count)
    return cols


def merge_ranges(ranges: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    if not ranges:
        return []
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start - last_end <= gap:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def projection_ranges(values: list[int], min_count: int, min_size: int, gap: int) -> list[tuple[int, int]]:
    ranges = []
    start = None
    for index, value in enumerate(values):
        if value >= min_count and start is None:
            start = index
        elif value < min_count and start is not None:
            if index - start >= min_size:
                ranges.append((start, index))
            start = None
    if start is not None and len(values) - start >= min_size:
        ranges.append((start, len(values)))
    return merge_ranges(ranges, gap)


def detect_line_boxes(
    image: Image.Image,
    threshold: int,
    min_row_dark: int,
    min_col_dark: int,
    min_height: int,
    min_width: int,
    row_gap: int,
    col_gap: int,
    padding: int,
    max_area_ratio: float,
) -> list[Box]:
    width, height = image.size
    row_values = dark_row_projection(image, threshold)
    row_ranges = projection_ranges(row_values, min_row_dark, min_height, row_gap)
    boxes = []
    for top, bottom in row_ranges:
        col_values = dark_col_projection(image, threshold, top, bottom)
        col_ranges = projection_ranges(col_values, min_col_dark, min_width, col_gap)
        for left, right in col_ranges:
            box = Box(left, top, right, bottom).padded(padding, image.size)
            if box.width < min_width or box.height < min_height:
                continue
            if box.area > width * height * max_area_ratio:
                continue
            boxes.append(box)
    return boxes


def draw_overlay(page_image: Image.Image, boxes: list[Box], output_path: Path) -> None:
    overlay = page_image.convert("RGBA")
    draw = ImageDraw.Draw(overlay, "RGBA")
    for index, box in enumerate(boxes, start=1):
        draw.rectangle(box.as_list(), outline=(20, 110, 220, 220), width=3, fill=(20, 110, 220, 12))
        draw.text((box.left + 8, box.top + 6), str(index), fill=(0, 55, 130, 255))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.convert("RGB").save(output_path)


def rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_candidates(args: argparse.Namespace) -> dict:
    output = args.output
    pages_dir = output / "pages"
    crops_dir = output / "crops"
    overlays_dir = output / "overlays"
    pages = render_pages(args.pdf, pages_dir, args.scale)
    all_candidates = []
    page_records = []

    for page_info in pages:
        page_number = page_info["page"]
        image_path = page_info["image_path"]
        image = Image.open(image_path).convert("RGB")
        boxes = detect_line_boxes(
            image=image,
            threshold=args.threshold,
            min_row_dark=args.min_row_dark,
            min_col_dark=args.min_col_dark,
            min_height=args.min_height,
            min_width=args.min_width,
            row_gap=args.row_gap,
            col_gap=args.col_gap,
            padding=args.padding,
            max_area_ratio=args.max_area_ratio,
        )

        page_crop_dir = crops_dir / f"page_{page_number:03d}"
        page_crop_dir.mkdir(parents=True, exist_ok=True)
        page_candidates = []
        overlay_path = overlays_dir / f"page_{page_number:03d}.png"
        for index, box in enumerate(boxes, start=1):
            candidate_id = f"p{page_number:03d}_r{index:03d}"
            crop_path = page_crop_dir / f"{candidate_id}.png"
            image.crop(tuple(box.as_list())).save(crop_path)
            row = {
                "id": candidate_id,
                "page": page_number,
                "bbox": json.dumps(box.as_list()),
                "crop_path": rel(crop_path, output),
                "overlay_path": rel(overlay_path, output),
                "printed_zhuyin": "",
                "expected_zhuyin": "",
                "suspected_error": "uncertain",
                "crop_quality": "unknown",
                "note": "",
            }
            all_candidates.append(row)
            page_candidates.append(row)

        draw_overlay(image, boxes, overlay_path)
        page_records.append(
            {
                "page": page_number,
                "image_path": rel(image_path, output),
                "overlay_path": rel(overlay_path, output),
                "width": image.width,
                "height": image.height,
                "candidates": page_candidates,
            }
        )

    payload = {"pdf": str(args.pdf), "scale": args.scale, "pages": page_records, "candidates": all_candidates}
    write_csv(all_candidates, output / "candidates.csv")
    (output / "candidates.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_review_html(payload: dict, output: Path) -> None:
    data = json.dumps(payload, ensure_ascii=False)
    page_options = "\n".join(
        f'<button class="page-button" data-page="{page["page"]}">{page["page"]:02d}</button>'
        for page in payload["pages"]
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Single PDF Zhuyin Review</title>
  <style>
    :root {{
      --bg: #f5f6f8;
      --panel: #ffffff;
      --ink: #111827;
      --muted: #526174;
      --line: #d7dde7;
      --accent: #1463d8;
      --error: #b42318;
      --ok: #087443;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0; font-size: 17px; letter-spacing: 0; }}
    main {{
      display: grid;
      grid-template-columns: minmax(520px, 1fr) 440px;
      min-height: calc(100vh - 56px);
    }}
    .viewer {{ padding: 14px; overflow: auto; }}
    .toolbar {{
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }}
    .page-button, button, select, input, textarea {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      min-height: 34px;
      padding: 6px 10px;
      font: inherit;
    }}
    .page-button.active {{
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 700;
    }}
    button.primary {{
      background: var(--accent);
      border-color: var(--accent);
      color: white;
      font-weight: 700;
    }}
    .stage {{
      position: relative;
      width: min(100%, 980px);
      background: #fff;
      border: 1px solid var(--line);
      overflow: hidden;
      touch-action: none;
    }}
    .stage img {{ width: 100%; display: block; user-select: none; }}
    .box {{
      position: absolute;
      border: 2px solid rgba(20, 99, 216, .95);
      background: rgba(20, 99, 216, .08);
      cursor: pointer;
    }}
    .box.manual {{ border-color: var(--ok); background: rgba(8, 116, 67, .1); }}
    .box.active {{ border-color: var(--error); background: rgba(180, 35, 24, .12); }}
    .box span {{
      position: absolute;
      top: 2px;
      left: 3px;
      background: rgba(255,255,255,.88);
      color: var(--accent);
      font-size: 11px;
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 4px;
    }}
    .draft {{
      position: absolute;
      border: 2px dashed var(--ok);
      background: rgba(8, 116, 67, .08);
      pointer-events: none;
    }}
    .side {{
      border-left: 1px solid var(--line);
      background: var(--panel);
      overflow: auto;
      padding: 16px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 14px;
      margin-bottom: 12px;
      color: var(--muted);
    }}
    .crop {{
      border: 1px solid var(--line);
      background: #fff;
      width: 100%;
      min-height: 140px;
      margin-bottom: 14px;
    }}
    label {{ display: block; font-weight: 700; margin: 10px 0 5px; }}
    input, textarea, select {{ width: 100%; }}
    textarea {{ min-height: 80px; resize: vertical; }}
    .list {{ display: grid; gap: 8px; margin-top: 14px; }}
    .candidate-button {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      text-align: left;
      border-radius: 6px;
      padding: 8px;
    }}
    .candidate-button.active {{
      border-color: var(--accent);
      box-shadow: 0 0 0 1px var(--accent) inset;
    }}
    .small {{ color: var(--muted); font-size: 12px; }}
    @media (max-width: 980px) {{
      main {{ grid-template-columns: 1fr; }}
      .side {{ border-left: 0; border-top: 1px solid var(--line); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Single PDF Zhuyin Review</h1>
    <button class="primary" id="exportButton">Export JSON</button>
  </header>
  <main>
    <section class="viewer">
      <div class="toolbar">
        {page_options}
        <button id="drawButton">Draw box</button>
      </div>
      <div class="stage" id="stage">
        <img id="pageImage" alt="">
      </div>
    </section>
    <aside class="side">
      <div class="meta">
        <div><strong id="candidateId"></strong></div>
        <div id="pageLabel"></div>
        <div id="bboxLabel" class="small"></div>
        <div id="countLabel" class="small"></div>
      </div>
      <canvas class="crop" id="cropCanvas"></canvas>
      <label for="printed">printed_zhuyin</label>
      <input id="printed" placeholder="what is printed">
      <label for="expected">expected_zhuyin</label>
      <input id="expected" placeholder="standard pronunciation">
      <label for="suspected">suspected_error</label>
      <select id="suspected">
        <option>uncertain</option>
        <option>yes</option>
        <option>no</option>
      </select>
      <label for="quality">crop_quality</label>
      <select id="quality">
        <option>unknown</option>
        <option>good</option>
        <option>weak</option>
        <option>bad</option>
      </select>
      <label for="note">note</label>
      <textarea id="note"></textarea>
      <div class="list" id="candidateList"></div>
    </aside>
  </main>
  <script>
    const payload = {data};
    const saved = JSON.parse(localStorage.getItem("singlePdfZhuyinReview") || "{{}}");
    const manual = JSON.parse(localStorage.getItem("singlePdfZhuyinManualBoxes") || "[]");
    const byPage = new Map(payload.pages.map(page => [page.page, page]));
    let currentPage = payload.pages[0].page;
    let currentCandidate = payload.pages[0].candidates[0]?.id || "";
    let drawMode = false;
    let dragStart = null;
    let draftNode = null;

    function pageCandidates(page) {{
      return page.candidates.concat(manual.filter(item => item.page === page.page));
    }}

    function candidateById(id) {{
      return payload.candidates.concat(manual).find(item => item.id === id);
    }}

    function stateFor(id) {{
      const base = candidateById(id);
      return Object.assign({{}}, base, saved[id] || {{}});
    }}

    function saveCurrent() {{
      if (!currentCandidate) return;
      saved[currentCandidate] = {{
        printed_zhuyin: document.getElementById("printed").value,
        expected_zhuyin: document.getElementById("expected").value,
        suspected_error: document.getElementById("suspected").value,
        crop_quality: document.getElementById("quality").value,
        note: document.getElementById("note").value
      }};
      localStorage.setItem("singlePdfZhuyinReview", JSON.stringify(saved));
    }}

    function renderPage() {{
      const page = byPage.get(currentPage);
      document.getElementById("pageImage").src = page.image_path;
      document.querySelectorAll(".page-button").forEach(button => {{
        button.classList.toggle("active", Number(button.dataset.page) === currentPage);
      }});
      const candidates = pageCandidates(page);
      if (!candidates.some(item => item.id === currentCandidate)) {{
        currentCandidate = candidates[0]?.id || "";
      }}
      renderBoxes(page);
      renderList(page);
      renderForm();
    }}

    function renderBoxes(page) {{
      const stage = document.getElementById("stage");
      stage.querySelectorAll(".box").forEach(node => node.remove());
      const scale = stage.clientWidth / page.width;
      pageCandidates(page).forEach((candidate, index) => {{
        const box = JSON.parse(candidate.bbox);
        const node = document.createElement("button");
        node.className = "box";
        node.classList.toggle("manual", candidate.manual === true);
        node.style.left = `${{box[0] * scale}}px`;
        node.style.top = `${{box[1] * scale}}px`;
        node.style.width = `${{(box[2] - box[0]) * scale}}px`;
        node.style.height = `${{(box[3] - box[1]) * scale}}px`;
        node.innerHTML = `<span>${{index + 1}}</span>`;
        node.classList.toggle("active", candidate.id === currentCandidate);
        node.addEventListener("click", () => {{
          saveCurrent();
          currentCandidate = candidate.id;
          renderPage();
        }});
        stage.appendChild(node);
      }});
    }}

    function renderList(page) {{
      const list = document.getElementById("candidateList");
      list.innerHTML = "";
      pageCandidates(page).forEach(candidate => {{
        const state = stateFor(candidate.id);
        const button = document.createElement("button");
        button.className = "candidate-button";
        button.classList.toggle("active", candidate.id === currentCandidate);
        button.innerHTML = `
          <span><strong>${{candidate.id}}</strong><br><span class="small">${{state.suspected_error}} / ${{state.crop_quality}}</span></span>
          <span class="small">${{candidate.manual ? "manual" : "auto"}}</span>
        `;
        button.addEventListener("click", () => {{
          saveCurrent();
          currentCandidate = candidate.id;
          renderPage();
        }});
        list.appendChild(button);
      }});
    }}

    function renderForm() {{
      const candidate = stateFor(currentCandidate);
      if (!candidate) return;
      document.getElementById("candidateId").textContent = candidate.id;
      document.getElementById("pageLabel").textContent = `page ${{candidate.page}}`;
      document.getElementById("bboxLabel").textContent = candidate.bbox;
      document.getElementById("countLabel").textContent = `${{payload.candidates.length + manual.length}} candidates`;
      renderCrop(candidate);
      document.getElementById("printed").value = candidate.printed_zhuyin || "";
      document.getElementById("expected").value = candidate.expected_zhuyin || "";
      document.getElementById("suspected").value = candidate.suspected_error || "uncertain";
      document.getElementById("quality").value = candidate.crop_quality || "unknown";
      document.getElementById("note").value = candidate.note || "";
    }}

    function renderCrop(candidate) {{
      const canvas = document.getElementById("cropCanvas");
      const context = canvas.getContext("2d");
      const page = byPage.get(candidate.page);
      const image = new Image();
      image.onload = () => {{
        const box = JSON.parse(candidate.bbox);
        const sourceWidth = Math.max(1, box[2] - box[0]);
        const sourceHeight = Math.max(1, box[3] - box[1]);
        const targetWidth = 400;
        const targetHeight = Math.max(120, Math.round(targetWidth * sourceHeight / sourceWidth));
        canvas.width = targetWidth;
        canvas.height = targetHeight;
        context.fillStyle = "#fff";
        context.fillRect(0, 0, targetWidth, targetHeight);
        context.drawImage(image, box[0], box[1], sourceWidth, sourceHeight, 0, 0, targetWidth, targetHeight);
      }};
      image.src = page.image_path;
    }}

    function exportJson() {{
      saveCurrent();
      const rows = payload.candidates.concat(manual).map(item => Object.assign({{}}, item, saved[item.id] || {{}}));
      const blob = new Blob([JSON.stringify({{candidates: rows}}, null, 2)], {{type: "application/json"}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "review-notes.json";
      link.click();
      URL.revokeObjectURL(url);
    }}

    function stagePoint(event) {{
      const stage = document.getElementById("stage");
      const rect = stage.getBoundingClientRect();
      const page = byPage.get(currentPage);
      const scale = page.width / rect.width;
      return {{
        x: Math.max(0, Math.min(page.width, Math.round((event.clientX - rect.left) * scale))),
        y: Math.max(0, Math.min(page.height, Math.round((event.clientY - rect.top) * scale)))
      }};
    }}

    function updateDraftBox(start, end) {{
      const stage = document.getElementById("stage");
      const page = byPage.get(currentPage);
      const scale = stage.clientWidth / page.width;
      if (!draftNode) {{
        draftNode = document.createElement("div");
        draftNode.className = "draft";
        stage.appendChild(draftNode);
      }}
      draftNode.style.left = `${{Math.min(start.x, end.x) * scale}}px`;
      draftNode.style.top = `${{Math.min(start.y, end.y) * scale}}px`;
      draftNode.style.width = `${{Math.abs(start.x - end.x) * scale}}px`;
      draftNode.style.height = `${{Math.abs(start.y - end.y) * scale}}px`;
    }}

    function createManualCandidate(start, end) {{
      const left = Math.min(start.x, end.x);
      const top = Math.min(start.y, end.y);
      const right = Math.max(start.x, end.x);
      const bottom = Math.max(start.y, end.y);
      if (right - left < 20 || bottom - top < 20) return;
      const id = `manual_p${{String(currentPage).padStart(3, "0")}}_${{Date.now()}}`;
      const item = {{
        id,
        page: currentPage,
        bbox: JSON.stringify([left, top, right, bottom]),
        crop_path: "",
        overlay_path: "",
        printed_zhuyin: "",
        expected_zhuyin: "",
        suspected_error: "uncertain",
        crop_quality: "unknown",
        note: "",
        manual: true
      }};
      manual.push(item);
      localStorage.setItem("singlePdfZhuyinManualBoxes", JSON.stringify(manual));
      currentCandidate = id;
    }}

    document.querySelectorAll(".page-button").forEach(button => {{
      button.addEventListener("click", () => {{
        saveCurrent();
        currentPage = Number(button.dataset.page);
        renderPage();
      }});
    }});
    ["printed", "expected", "suspected", "quality", "note"].forEach(id => {{
      document.getElementById(id).addEventListener("input", saveCurrent);
      document.getElementById(id).addEventListener("change", saveCurrent);
    }});
    document.getElementById("exportButton").addEventListener("click", exportJson);
    document.getElementById("drawButton").addEventListener("click", () => {{
      drawMode = !drawMode;
      document.getElementById("drawButton").classList.toggle("primary", drawMode);
    }});
    document.getElementById("stage").addEventListener("pointerdown", event => {{
      if (!drawMode) return;
      dragStart = stagePoint(event);
      updateDraftBox(dragStart, dragStart);
    }});
    document.getElementById("stage").addEventListener("pointermove", event => {{
      if (!drawMode || !dragStart) return;
      updateDraftBox(dragStart, stagePoint(event));
    }});
    document.getElementById("stage").addEventListener("pointerup", event => {{
      if (!drawMode || !dragStart) return;
      saveCurrent();
      createManualCandidate(dragStart, stagePoint(event));
      dragStart = null;
      if (draftNode) draftNode.remove();
      draftNode = null;
      renderPage();
    }});
    window.addEventListener("resize", renderPage);
    document.getElementById("pageImage").addEventListener("load", () => renderBoxes(byPage.get(currentPage)));
    renderPage();
  </script>
</body>
</html>
"""
    (output / "review.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a static review UI for one image-only PDF.")
    parser.add_argument("--pdf", type=Path, default=Path("sample.pdf"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/full_audit"))
    parser.add_argument("--scale", type=float, default=2.5)
    parser.add_argument("--threshold", type=int, default=130)
    parser.add_argument("--min-row-dark", type=int, default=80)
    parser.add_argument("--min-col-dark", type=int, default=3)
    parser.add_argument("--min-height", type=int, default=18)
    parser.add_argument("--min-width", type=int, default=44)
    parser.add_argument("--row-gap", type=int, default=8)
    parser.add_argument("--col-gap", type=int, default=20)
    parser.add_argument("--padding", type=int, default=12)
    parser.add_argument("--max-area-ratio", type=float, default=0.006)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    payload = build_candidates(args)
    write_review_html(payload, args.output)
    print(args.output / "review.html")
    print(f"pages={len(payload['pages'])}")
    print(f"candidates={len(payload['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
