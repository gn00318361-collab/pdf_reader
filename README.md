# 校刊注音破音字審稿助手

這個 repo 的目標不是建立完整自動化注音 OCR，而是針對目前這份校刊 PDF，做一個實用的「破音字／多音字風險審稿助手」。

目前的任務已經重新收斂為：

1. 只處理 `data/raw/sample.pdf` 這份 44 頁校刊 PDF。
2. 優先辨識頁面中的中文正文，不辨識旁邊的小注音。
3. 根據破音字與多音字詞庫，找出高風險詞。
4. 產生人工 review 清單，讓老師快速確認 PDF 上實際標示的注音是否正確。

## 為什麼不先做注音 OCR

昨天的實驗已經確認，直接做「逐字切割 + 注音辨識 + 自動判錯」會同時卡在版面分析、中文字定位、注音 OCR、語境判讀四個難題。尤其是注音符號很小、聲調符號容易誤判，而且單字截圖會失去上下文。

因此第一版採用更務實的人機協作設計：

> 系統負責找出最值得檢查的位置，人類負責最後一眼確認。

## 預計流程

```text
data/raw/sample.pdf
  ↓
指定頁面轉成高解析圖片
  ↓
OCR 只抽取中文正文
  ↓
整理每頁 OCR 文字
  ↓
用破音字／多音字詞庫掃描高風險詞
  ↓
產生 review_candidates.json 與 review.html
  ↓
老師根據候選清單人工確認
```

## 目錄結構

```text
.
├── README.md
├── data/
│   └── raw/
│       └── sample.pdf
├── docs/
│   ├── architecture.md
│   ├── handoff_5080_pc.md
│   ├── implementation_plan.md
│   └── research/
│       └── new_plan.md
├── outputs/
│   ├── ocr/
│   ├── pages/
│   └── review/
└── src/
```

## 第一版成功標準

第一版不要求精準框出每個字，也不要求判斷 PDF 上實際印出的注音。

第一版只需要做到：

1. 能把指定頁面轉成圖片。
2. 能對每頁做中文正文 OCR。
3. 能掃描出破音字／多音字高風險詞。
4. 能輸出候選清單，包含頁碼、詞、應檢查字、正確注音、原因與 OCR 上下文。

候選資料格式範例：

```json
{
  "page": 22,
  "matched_word": "成為",
  "target_char": "為",
  "expected_bopomofo": "ㄨㄟˊ",
  "reason": "「成為」中的「為」應讀二聲，不是四聲。",
  "ocr_context": "..."
}
```

## 下一步

請從 `docs/handoff_5080_pc.md` 開始看，接著依照 `docs/implementation_plan.md` 實作 MVP。

## 目前可執行的 MVP

已建立第一版 pipeline，可以先用第 22 頁 regression case 驗證：

```powershell
python src\run_pipeline.py --pages 22 --dpi 300 --engine rapidocr --gpu
```

輸出包含：

```text
outputs/pages/page_022.png
outputs/pages/page_022_annotated.png
outputs/ocr/page_022.json
outputs/review/review_candidates.json
outputs/review/review.html
```

`page_022_annotated.png` 會把 OCR 偵測到的文字區塊標上 `T001`、`T002` 等 ID；命中破音詞庫的區塊會用橘色標出。`review.html` 是第一版靜態 dashboard，方便人工依頁碼與 token ID 回查。

目前 RapidOCR 在這台 PC 可穩定跑通。ONNXRuntime 已偵測到 CUDA provider，但目前缺 CUDA 12 / cuDNN 9 runtime 依賴，會自動退回 CPU provider；功能流程不受影響，GPU 加速可作為下一步環境優化。

若要跑所有指定頁：

```powershell
python src\run_pipeline.py --pages "1,4,5,13,15,16-27,30-42" --dpi 300 --engine rapidocr --gpu
```
