# 實作計畫

## 階段 0：確認環境

目標是先確認 PDF 可以轉圖，並且至少有一個中文 OCR 工具能處理單頁。

建議順序：

1. 安裝 PDF 渲染工具，例如 PyMuPDF。
2. 嘗試將第 22 頁轉成 300 DPI 或 400 DPI PNG。
3. 安裝並測試 PaddleOCR。
4. 如果 PaddleOCR 環境卡住，先改用其他可用 OCR 工具，不要在環境問題上消耗太久。

## 階段 1：頁面渲染

建立 `src/render_pages.py`。

輸入：

```text
data/raw/sample.pdf
```

輸出：

```text
outputs/pages/page_001.png
outputs/pages/page_004.png
...
```

第一版指定頁面：

```text
1, 4, 5, 13, 15, 16-27, 30-42
```

如果要快速驗證，可以先只跑：

```text
22
```

## 階段 2：中文正文 OCR

建立 `src/ocr_pages.py`。

輸入：

```text
outputs/pages/*.png
```

輸出：

```text
outputs/ocr/page_022.json
```

建議資料格式：

```json
{
  "page": 22,
  "text": "整頁 OCR 合併文字",
  "items": [
    {
      "text": "成為",
      "confidence": 0.98,
      "box": [[0, 0], [100, 0], [100, 30], [0, 30]]
    }
  ]
}
```

如果 OCR 工具輸出的順序很亂，第一版可以先保留原始 items，並另外做一個粗略的 `text` 欄位給詞庫掃描。

## 階段 3：破音詞庫

建立 `data/risk_terms.json`。

第一版詞庫可以從高 ROI 詞開始，不必一次做完整字典。

建議先放：

```json
[
  {
    "matched_word": "成為",
    "target_char": "為",
    "expected_bopomofo": "ㄨㄟˊ",
    "reason": "「成為」中的「為」應讀二聲，不是四聲。",
    "confidence": "high"
  },
  {
    "matched_word": "因為",
    "target_char": "為",
    "expected_bopomofo": "ㄨㄟˋ",
    "reason": "「因為」中的「為」應讀四聲。",
    "confidence": "high"
  },
  {
    "matched_word": "音樂",
    "target_char": "樂",
    "expected_bopomofo": "ㄩㄝˋ",
    "reason": "「音樂」中的「樂」應讀 ㄩㄝˋ。",
    "confidence": "high"
  },
  {
    "matched_word": "快樂",
    "target_char": "樂",
    "expected_bopomofo": "ㄌㄜˋ",
    "reason": "「快樂」中的「樂」應讀 ㄌㄜˋ。",
    "confidence": "high"
  },
  {
    "matched_word": "重新",
    "target_char": "重",
    "expected_bopomofo": "ㄔㄨㄥˊ",
    "reason": "「重新」中的「重」應讀 ㄔㄨㄥˊ。",
    "confidence": "high"
  },
  {
    "matched_word": "重要",
    "target_char": "重",
    "expected_bopomofo": "ㄓㄨㄥˋ",
    "reason": "「重要」中的「重」應讀 ㄓㄨㄥˋ。",
    "confidence": "high"
  },
  {
    "matched_word": "覺得",
    "target_char": "得",
    "expected_bopomofo": "ㄉㄜ˙",
    "reason": "「覺得」中的「得」常讀輕聲。",
    "confidence": "medium"
  },
  {
    "matched_word": "了解",
    "target_char": "了",
    "expected_bopomofo": "ㄌㄧㄠˇ",
    "reason": "「了解」中的「了」應讀 ㄌㄧㄠˇ。",
    "confidence": "high"
  }
]
```

## 階段 4：候選掃描

建立 `src/scan_candidates.py`。

輸入：

```text
outputs/ocr/*.json
data/risk_terms.json
```

輸出：

```text
outputs/review/review_candidates.json
```

候選格式：

```json
{
  "page": 22,
  "matched_word": "成為",
  "target_char": "為",
  "expected_bopomofo": "ㄨㄟˊ",
  "reason": "「成為」中的「為」應讀二聲，不是四聲。",
  "confidence": "high",
  "ocr_context": "..."
}
```

## 階段 5：HTML review 報告

建立 `src/build_review.py`。

第一版 HTML 只要能讓老師快速掃描：

1. 頁碼。
2. 高風險詞。
3. 應檢查字。
4. 正確注音。
5. 原因。
6. OCR 上下文。

輸出：

```text
outputs/review/review.html
```

## 階段 6：局部截圖

等階段 1 到 5 穩定後，再處理局部截圖。

這一階段才需要利用 OCR 的 bounding box，找出高風險詞附近的行或區塊，截出比較寬的上下文圖片。

注意：不要回到逐字切割。局部截圖應該是「方便人工看」的輔助，而不是讓模型判斷注音。

## 最小驗收清單

1. 可以重跑整個流程。
2. 可以針對第 22 頁命中「成為」。
3. 可以產生 `outputs/review/review_candidates.json`。
4. 可以產生 `outputs/review/review.html`。
5. 文件與報告使用繁體中文。

## 目前實作狀態

第一版已加入：

1. `src/render_pages.py`：指定頁 PDF 轉 PNG。
2. `src/ocr_pages.py`：OCR 文字區塊、輸出每頁 JSON、產生 annotated overlay。
3. `src/scan_candidates.py`：掃描破音詞庫並輸出候選清單。
4. `src/build_review.py`：產生靜態 HTML review dashboard。
5. `src/run_pipeline.py`：串起第 22 頁或指定頁面的完整流程。

目前預設 OCR engine 是 RapidOCR，因為它在 Windows / Python 3.12 上已穩定跑通。PaddleOCR 仍保留為可選 engine，但目前這台機器上的 Paddle CPU build 會撞到 oneDNN/PIR runtime 問題。

第 22 頁驗證指令：

```powershell
python src\run_pipeline.py --pages 22 --dpi 300 --engine rapidocr --gpu
```

目前 `--gpu` 會要求 ONNXRuntime 使用 CUDA provider。GPU runtime 已透過 Python 環境中的 NVIDIA CUDA/cuDNN wheels 補齊，可用下列指令驗證：

```powershell
python src\check_gpu_runtime.py
```

通過時應看到 ONNXRuntime session 與 RapidOCR det/cls/rec sessions 都以 `CUDAExecutionProvider` 為第一順位。

## 新階段：有限 corpus 索引

固定 `risk_terms.json` 只能找已知詞。針對目前這份 PDF，應先利用 OCR 結果建立有限 corpus，列出實際出現的多音字與上下文。

執行：

```powershell
python src\build_corpus_index.py --pages "1,4,5,13,15,16-27,30-42" --radius 4
```

輸出：

1. `outputs/review/corpus.json`：所有 OCR regions 與全文。
2. `outputs/review/char_index.json`：多音字出現位置、頁碼、token、上下文。
3. `outputs/review/context_candidates.json`：去重後的上下文候選。
4. `outputs/review/corpus_summary.md`：人工快速閱讀摘要。

下一步應基於這些實際出現的上下文，產生更精準的詞級候選，而不是盲目擴充全中文世界的破音詞庫。

## 詞級候選整理

在 `char_index.json` 產生後，可建立詞級候選：

```powershell
python src\build_phrase_index.py --left 2 --right 2
python src\build_phrase_review.py
```

輸出：

1. `outputs/review/phrase_occurrences.json`：每個多音字 occurrence 的候選短語、估算詞級 bbox、截圖路徑。
2. `outputs/review/phrase_terms.json`：依候選短語聚合後的統計。
3. `outputs/review/phrase_summary.md`：高頻候選短語摘要。
4. `outputs/review/phrase_review.html`：可搜尋、可切換深色模式的詞級候選 dashboard。

目前詞級 bbox 是根據 OCR region 與字元位置比例估算，目的是比整行框更方便人工檢查；它不是獨立模型偵測出的真實詞框。

## 詞級候選判讀與排序

詞級候選整理後，下一層不是擴充全中文破音詞庫，而是在這份 PDF 的有限 corpus 上套用可控規則，先把高確定性的 occurrence 標出來：

```powershell
python src\score_phrase_candidates.py
python src\build_scored_review.py
```

輸出：

1. `outputs/review/scored_phrase_candidates.json`：所有詞級 occurrence 的判讀狀態、優先級、推估注音與命中規則。
2. `outputs/review/reviewable_phrase_candidates.json`：目前已由規則命中的 occurrence。
3. `outputs/review/scored_summary.md`：規則命中數、未解析數、命中字與 pattern 統計。
4. `outputs/review/scored_review.html`：可搜尋、可依 priority/status 篩選、可切換深色模式的審核 dashboard；標記圖會開新分頁，待審候選可分頁並調整每頁筆數，已檢查列可勾選後移到頁面底部的 Checked 區塊。

規則來源是 `data/reading_rules.json`。規則比對只看候選短語、詞級 options 與該 occurrence 附近 context，不用整段 OCR region 直接命中，避免同一行裡其他詞把目前候選誤判成已解析。

目前指定頁驗證結果：

1. 詞級 occurrence：473
2. 規則命中：202
3. 未解析：271
4. 優先級分布：high 116、medium 85、low 1、unresolved 271

## JSON semantic second pass

下一層架構修正為：Codex / LLM 不看圖片、不操控 dashboard 做逐字視覺審稿，而是讀 JSON context 做語境判讀。OCR/layout pipeline 的責任是把 PDF 轉成可追溯文字索引；規則或 LLM 的責任是從索引中挑出真正值得人工看的候選。

流程：

```text
OCR JSON
  ↓
full char occurrence index
  ↓
cheap filter / semantic targets
  ↓
rules or LLM semantic classifier
  ↓
review candidates dashboard
```

### Full char occurrence index

執行：

```powershell
python src\build_char_occurrences.py --pages "1,4,5,13,15,16-27,30-42"
```

輸出：

1. `outputs/review/char_occurrences.jsonl`：每個中文字一筆，包含 `id`、page、region、字元位置、context windows、region text、OCR confidence、region bbox、estimated char bbox、page/annotated image path。
2. `outputs/review/char_occurrences_meta.json`：全字索引基本統計。
3. `outputs/review/char_occurrences_summary.md`：每頁中文字數與字頻摘要。

目前結果：

1. 中文字 occurrence：13,782
2. 不重複中文字：1,336
3. 頁面數：30

`estimated_char_bbox` 是從 OCR region bbox 與字元 index 比例估算，不代表模型真的逐字偵測；它是定位輔助，不是最終審稿依據。

### Semantic targets

執行：

```powershell
python src\build_semantic_targets.py
```

輸出：

1. `outputs/review/semantic_targets.jsonl`：cheap filter 後的語境判讀目標。
2. `outputs/review/semantic_targets_meta.json`：semantic target 統計。
3. `outputs/review/semantic_targets_summary.md`：trigger、risk level、字分布摘要。

目前 cheap filter 觸發條件：

1. `polyphonic_char`：字出現在 `data/polyphonic_chars.json`。
2. `phrase_rule_match`：`risk_terms.json` 或 `reading_rules.json` 的詞語規則精準覆蓋目前這個 char index。
3. `low_confidence_polyphonic`：OCR confidence 低於 threshold 且該字在多音字表中。

目前結果：

1. semantic targets：473
2. phrase rule match：202
3. 需要 semantic classifier 補判：271

這代表現有 473 不是最終真理，而是基於目前多音字表與規則集產生的 semantic targets v0。之後若補上更多多音字，只需更新 `polyphonic_chars.json` 並重跑 char index / semantic target，不必重跑 OCR。

### Semantic classifier

在 `semantic_targets.jsonl` 產生後，可用本地規則型 classifier 先補判理論正確讀音：

```powershell
python src\classify_semantic_targets.py
python src\build_scored_review.py
```

輸出：

1. `outputs/review/semantic_review_candidates.jsonl`：JSONL 版 classifier 結果。
2. `outputs/review/semantic_review_candidates.json`：dashboard 可直接讀取的 JSON 版 classifier 結果。
3. `outputs/review/semantic_review_candidates_meta.json`：分類統計。
4. `outputs/review/semantic_classifier_summary.md`：分類狀態、priority、字分布摘要。

`src/build_scored_review.py` 會優先使用 `semantic_review_candidates.json`，讓第一條人工審稿 dashboard 直接吃第二階段補判結果；若檔案不存在，才退回舊的 `scored_phrase_candidates.json`。

目前結果：

1. review candidates：473
2. 已有理論讀音：450
3. 仍未解析：23
4. `rule_carried`：202
5. `semantic_rule_matched`：93
6. `default_by_char_context`：155
7. `semantic_unresolved`：23

這一層沒有看圖片，也沒有自動確認 PDF 上印出的注音是否正確。它只根據中文 context 補上「理論正確讀音」與 reason，最後仍由 dashboard 讓人工看 crop / annotated page 做確認。

### Review state / issue handoff

dashboard 的人工標記分成兩種：

1. `檢查`：人工看過，移到 Checked 區塊。
2. `有錯`：疑似注音錯或需要修正，紅色 highlight 並移到 Issues 區塊。

標記會先存在瀏覽器 `localStorage`，避免重新整理後消失。若要交接給朋友或另一個 Codex，可使用 dashboard 的 `匯出標記` 下載 `review_state.json`，再把內容更新到 repo 中的：

```text
data/review_state.json
```

這份檔案的 schema 是 `pdf_reader_review_state.v1`，包含 `reviewed_ids`、`issue_ids` 與 `issues` 明細。對方可以直接讀 JSON，或在 dashboard 使用 `匯入標記` 載回狀態，快速定位被標記的頁碼、區塊、候選短語與原因。
