# 架構設計

## 核心定位

本專案定位為「破音字／多音字風險審稿助手」，不是完整自動化注音校稿器。

系統不嘗試直接辨識 PDF 上每個中文字旁邊的注音，也不在第一版判斷注音是否印錯。系統只負責根據中文正文找出高風險詞，並提供正確注音與上下文，讓人工快速確認。

## 設計原則

1. 先解決老師最痛的工作量問題，而不是追求全自動。
2. 優先使用成熟中文 OCR 辨識正文，不碰小尺寸注音 OCR。
3. 用破音詞庫縮小審查範圍。
4. 每一步都輸出中間產物，方便人工檢查與除錯。
5. 先支援目前這份 `sample.pdf`，不要過早泛化成通用產品。

## 系統流程

```text
PDF 原始檔
  ↓
頁面渲染
  ↓
中文 OCR
  ↓
文字正規化
  ↓
破音詞庫掃描
  ↓
候選清單產生
  ↓
HTML review 報告
```

## 模組規劃

### `src/render_pages.py`

負責將 `data/raw/sample.pdf` 的指定頁面轉成高解析圖片。

建議先支援：

1. 指定頁碼清單。
2. 設定 DPI，例如 300 或 400。
3. 輸出到 `outputs/pages/`。

### `src/ocr_pages.py`

負責對頁面圖片做中文 OCR。

第一優先建議測試 PaddleOCR，因為它能回傳文字與 bounding box，後續若要做局部截圖會比較方便。

第一版輸出到 `outputs/ocr/`，每頁一份 JSON：

```json
{
  "page": 22,
  "items": [
    {
      "text": "成為",
      "confidence": 0.98,
      "box": [[0, 0], [100, 0], [100, 30], [0, 30]]
    }
  ]
}
```

如果第一版 OCR 工具無法穩定提供 box，也可以先只輸出文字。頁碼與文字已經足以產生初版候選清單。

### `src/risk_lexicon.py`

負責載入與維護破音字／多音字詞庫。

詞庫建議放在 `data/risk_terms.json`，每個詞至少包含：

1. `matched_word`：要掃描的詞。
2. `target_char`：真正需要檢查的字。
3. `expected_bopomofo`：正確注音。
4. `reason`：為什麼這是高風險。
5. `confidence`：規則可信度。

### `src/scan_candidates.py`

負責掃描每頁 OCR 結果，找出詞庫命中的高風險詞。

輸出：

```text
outputs/review/review_candidates.json
```

### `src/build_review.py`

負責把候選清單整理成老師可讀的 HTML 報告。

第一版 HTML 應包含：

1. 頁碼。
2. 高風險詞。
3. 應檢查字。
4. 正確注音。
5. 風險原因。
6. OCR 上下文。

第二版再加入局部截圖。

## 資料流

```text
data/raw/sample.pdf
  -> outputs/pages/page_001.png
  -> outputs/ocr/page_001.json
  -> outputs/review/review_candidates.json
  -> outputs/review/review.html
```

## 非目標

第一版明確不做：

1. 不做注音 OCR。
2. 不做逐字切割。
3. 不訓練注音模型。
4. 不自動判斷 PDF 上實際印出的注音是否正確。
5. 不保證支援任意 PDF 版型。

## 後續擴充

等 MVP 能穩定產生候選清單後，可以再依序加入：

1. 根據 OCR bounding box 產生局部截圖。
2. 針對高風險詞所在行產生上下文截圖。
3. 加入人工標記介面，記錄「確認錯誤／確認正確」。
4. 再評估是否需要訓練或接入注音 OCR。
