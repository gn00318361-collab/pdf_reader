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
