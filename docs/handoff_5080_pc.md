# 5080 PC 交接說明

## 專案目前狀態

目前 repo 已經只保留與新方向相關的內容：

1. `data/raw/sample.pdf`：目前唯一要處理的 44 頁校刊 PDF。
2. `docs/research/new_plan.md`：昨天與今天重新整理問題、踩坑與新方向的完整討論紀錄。
3. `README.md`、`docs/architecture.md`、`docs/implementation_plan.md`：新的架構與實作計畫。

## 請先不要做的事

接手後請先避免以下方向：

1. 不要做注音 OCR。
2. 不要逐字切割中文字和注音。
3. 不要訓練注音辨識模型。
4. 不要要求 Gemma 或其他 VLM 判斷小注音聲調。
5. 不要把第一版做成通用 PDF 校稿工具。

這些都是昨天已經證明風險很高、容易拖垮 MVP 的方向。

## 請優先做的事

第一個目標是建立一條可跑通的 MVP pipeline：

```text
PDF 指定頁轉圖
  -> 中文正文 OCR
  -> 破音詞庫掃描
  -> review_candidates.json
  -> review.html
```

第一版即使沒有精準 bounding box，也可以接受。只要能列出「哪一頁出現哪些高風險詞」，就已經能降低人工校稿負擔。

## 建議指定頁面

先處理有注音審稿需求的頁面：

```text
1, 4, 5, 13, 15, 16-27, 30-42
```

如果 OCR 或 PDF 渲染流程尚未穩定，可以先只做第 22 頁，因為第 22 頁有重要 regression case：

```text
成為
```

其中「為」在「成為」中應讀 `ㄨㄟˊ`，不是單字預設常見的 `ㄨㄟˋ`。

## 5080 PC 的使用建議

5080 PC 的優勢主要在：

1. PaddleOCR GPU 推論。
2. 大量頁面 OCR 實驗。
3. 後續若要測試 local VLM，可以明顯加速。
4. 未來若真的要訓練注音 OCR，才需要 GPU。

但第一版不需要先上 VLM。請先用 OCR 與詞庫掃描完成最小可行版本。

## 建議第一個 Codex 任務

可以直接給 5080 PC 上的 Codex 這段任務：

```text
請依照 README.md、docs/architecture.md、docs/implementation_plan.md 實作 MVP。

目標：
1. 將 data/raw/sample.pdf 的指定頁轉成高解析 PNG。
2. 使用 PaddleOCR 或可用的中文 OCR 工具，只辨識正文中文字。
3. 建立 data/risk_terms.json 破音詞庫。
4. 掃描 OCR 結果，輸出 outputs/review/review_candidates.json。
5. 產生 outputs/review/review.html。

限制：
不要做注音 OCR。
不要逐字切割。
不要訓練模型。
不要使用 VLM 判斷聲調。
所有文件請用繁體中文。
```

## 驗收標準

MVP 完成時至少要能回答：

1. 第 22 頁是否能命中「成為」。
2. `review_candidates.json` 是否包含頁碼、詞、應檢查字、正確注音與原因。
3. `review.html` 是否能讓老師快速看懂要檢查什麼。
4. 執行流程是否可以重跑，不依賴手工改檔。
