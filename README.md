# PDF 注音校稿工具交接文件

這個專案的目標是協助小學老師校對教稿、校刊或教材 PDF 中的注音。文件中常見排版是「中文字旁邊並排注音符號」，人工校對時需要確認 PDF 上的注音是否符合教育部標準。

第一版目標不是自動改 PDF，而是自動產生「疑似注音錯誤清單」，讓老師或校稿人快速複核。

最新方向：不要再期待一般 OCR 直接讀完整頁中文字和小注音。實測後，專案核心應改成「先建立注音辨識 benchmark 與切割 pipeline；如果現成 OCR 無法達標，再訓練注音符號專用小模型」。

## 使用情境

老師收到一份 PDF 校稿稿件，裡面有中文與注音。若某個詞的注音錯了，例如「蛤蠣」的第二個字聲調標錯，老師希望系統能：

1. 讀取 PDF。
2. 找到中文字與它旁邊對應的注音。
3. 先篩出疑似有問題的詞或字。
4. 對疑似項目查教育部標準注音。
5. 輸出報告，標示頁碼、位置、PDF 上的注音、教育部標準注音與疑似錯誤原因。

範例校對來源：

- PDF：`/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf`
- 使用者提供截圖：`/Users/joneswang/Desktop/截圖 2026-06-04 下午1.30.33.png`
- 截圖指出第 39 頁有圈起來的注音錯誤。
- 教育部標準注音查詢範例：<https://dict.revised.moe.edu.tw/dictView.jsp?ID=68201&word=%E8%9B%A4%E8%A0%A3>
- 同一詞可用搜尋 URL 查詢：<https://dict.revised.moe.edu.tw/search.jsp?md=1&word=%E8%9B%A4%E8%A0%A3>

教育部頁面中「蛤蠣」的標準注音為：

```text
蛤蠣：ㄍㄜˊ ㄌㄧˋ
```

## 重要實測結論

使用者一開始以為範例 PDF 是文字型 PDF，但用 PyMuPDF 實測後，這份 PDF 實際上沒有可抽取文字層。

已執行檢查：

```bash
.venv/bin/python pdf_zhuyin_audit.py inspect "/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf" --page 39
```

結果：

```json
[
  {
    "page": 39,
    "text_chars": 0,
    "zhuyin_chars": 0,
    "images": 1,
    "fonts": 0,
    "is_extractable_text": false
  }
]
```

也跑過整份 PDF：

```text
pages: 44
extractable_pages: 0
image_only_pages: 44
```

結論：

- 這份範例 PDF 的 44 頁全部都是圖片頁。
- `PyMuPDF page.get_text()` 抽不到任何文字。
- 第 39 頁只有 1 張圖片，沒有 fonts，也沒有文字物件。
- 因此這份 PDF 不能走純文字座標解析，必須走 OCR。

如果未來拿到真正保留文字層的 PDF，流程可以簡化成「直接抽文字與座標」。但以目前這份範例檔為準，請下一位 Codex 直接以 OCR pipeline 規劃，不要假設有文字層。

## 方向調整：先 Benchmark，再決定是否訓練

已確認一般 OCR 不足以完成這個任務：

- Tesseract 加 `chi_tra` 可以抓到部分中文字，但會把注音讀成 `#`、`*`、數字或英文字母。
- Apple Vision OCR 可以抓到一些大字，但注音與中文字混在一起時輸出很亂。
- 第 22 頁已知錯誤是 `成為` 的 `為` 注音，不是先前誤判的 `心理方面`。這說明靠人工看圖或一般 OCR 在整頁中自由找錯，準確率不夠。

新的核心策略不是一開始訓練完整 OCR，而是先把問題拆小：

```text
1. PDF 頁面渲染成高解析圖片
2. 找出疑似有注音的區域
3. 針對已知錯誤案例做手動/半自動 crop benchmark
4. 測試現成 OCR 是否能讀出 PDF 上實際印的注音
5. 若現成 OCR 不行，再建立標註資料集
6. 訓練注音符號專用分類器
7. 將辨識結果接回教育部查詢與比對流程
```

這裡的「注音 OCR」不應一開始做成完整整頁 OCR。若需要訓練，第一版應是小型分類器：

```text
輸入：單一注音符號或聲調符號小圖
輸出：ㄅ / ㄆ / ㄇ / ... / ㄨ / ㄟ / ˊ / ˇ / ˋ / ˙
```

注音符號類別少，遠比中文字 OCR 容易。若只針對同一批教材、同一種字型與排版，模板比對或小型 CNN 都可能很快看到效果。

## Page 22 Benchmark 計畫

第一個任務不是訓練模型，而是建立可重複 benchmark。

Benchmark 目標：

```text
第 22 頁
詞語：成為
標準：ㄔㄥˊ ㄨㄟˊ
錯誤點：為 的注音聲調
問題：現成 OCR 能不能從 crop 圖讀出 PDF 實際印出的注音？
```

第一版 benchmark 應輸出：

```json
{
  "page": 22,
  "target_word": "成為",
  "expected_standard_zhuyin": "ㄔㄥˊ ㄨㄟˊ",
  "detected_pdf_zhuyin": "",
  "is_correct": false,
  "confidence": 0.0,
  "method": "tesseract_baseline",
  "crop_path": "artifacts/page22_benchmark/scale_4/target_chengwei_sharp.png"
}
```

Benchmark 要回答四個問題：

1. 是不是偵測不到注音？
2. 是不是 crop 範圍切錯？
3. 是不是聲調符號太小或太淡？
4. 是不是現成 OCR 不支援這種小注音？

只有 benchmark 顯示現成 OCR 都無法達標時，才進入訓練注音模型。

## 週末研究計畫

目標不是做完整產品，而是回答一個關鍵問題：

```text
我們能不能用可重複 benchmark，穩定切出並辨識第 22 頁「成為」中「為」旁邊的注音與聲調？
```

已知第 22 頁目標：

```text
頁碼：22
詞語：成為
標準注音：ㄔㄥˊ ㄨㄟˊ
問題：為 的注音有誤
```

### Day 1 上午：建立 Benchmark

1. 渲染第 22 頁為 300/450/600 DPI 等級圖片，或用 PyMuPDF scale 3/4/5 近似。
2. 手動設定 `成為` 附近 crop 區域。
3. 輸出原始 crop、放大 crop、二值化 crop、銳化 crop。
4. 分別用 Tesseract / Apple Vision / 其他 OCR 跑 baseline。
5. 將結果寫入 `artifacts/page22_benchmark/results.json`。

### Day 1 下午：決定是否需要訓練

如果現成 OCR 能讀出 `為` 旁邊的實際注音，先不要訓練，直接接比對流程。

如果現成 OCR 仍讀不到，才建立標註資料：

建議標註 CSV：

```csv
image_path,label,source_page,source_text,note
dataset/zhuyin/0001.png,ㄨ,22,成為,為的聲母/介音
dataset/zhuyin/0002.png,ㄟ,22,成為,為的韻母
dataset/zhuyin/0003.png,ˊ,22,成為,正確應為二聲
```

接著再做兩條路，哪條快就先用哪條：

1. 模板比對
   - 適合先驗證同一份 PDF、同一字型。
   - 對 `ˊ`、`ˋ` 這種聲調符號可能很有效。

2. 小型 CNN 分類器
   - 輸入小灰階圖，例如 32x32 或 48x48。
   - 類別為注音符號與聲調符號。
   - 5080 顯卡完全足夠，瓶頸在標註資料，不在訓練速度。

第一天 benchmark 驗收標準：

```text
能穩定產生「成為」附近 crop。
能保存不同 preprocessing 版本。
能記錄每個 OCR 方法的輸出。
能明確判定現成 OCR 是否足以讀出「為」旁邊的注音聲調。
```

### Day 2：擴到整頁候選

1. 對第 22 頁所有區域做文字候選擷取。
2. 對每個候選詞旁邊的注音小圖做分類。
3. 建立每個詞的 `pdf_zhuyin`。
4. 查教育部或本地詞典取得 `expected_zhuyin`。
5. 輸出 CSV/JSON 報告。

報告範例：

```json
{
  "page": 22,
  "candidate_text": "成為",
  "pdf_zhuyin": "ㄔㄥˊ ㄨㄟˋ",
  "expected_zhuyin": "ㄔㄥˊ ㄨㄟˊ",
  "status": "suspected_error",
  "reason": "tone_mismatch_on_為"
}
```

## 為什麼 5080 顯卡夠用

這不是大型語言模型或完整中文字 OCR 訓練。注音分類器的資料和模型都很小。

真正成本：

- 切圖品質。
- 標註資料量。
- 注音與中文字的座標配對規則。
- 聲調符號辨識準確率。

建議第一批資料量：

```text
每個常見注音符號 20-50 張
每個聲調符號 50-100 張
先集中在第 22 頁與同一份 PDF 的字型
```

若週末只做 MVP，可先只標 `成為` 相關類別：

```text
ㄔ ㄥ ㄨ ㄟ ˊ ˋ
```

成功後再擴充到完整注音符號集。

## 為什麼不能全部文字都查教育部

整份 PDF 的每個字、每個詞都送去教育部查詢不是好做法：

- 查詢量太大，速度慢，也可能對教育部網站造成壓力。
- 中文多音字很多，單字查詢容易誤判。
- 教材中有姓名、班級、標題、標點、錯切詞等情況，直接查全部會產生很多雜訊。
- OCR 會有辨識錯誤，應先用本地規則降低錯誤候選數。

正確策略是先建立「疑慮候選清單」，只把疑似錯誤或需要確認的詞送去教育部查核。

## 建議完整流水線

### 1. PDF 型態診斷

先判斷每一頁是否有可抽取文字層。

```text
PDF
-> PyMuPDF inspect
-> 若 text_chars > 0：文字層流程
-> 若 text_chars = 0：OCR 流程
```

目前範例 PDF 屬於 OCR 流程。

### 2. 頁面渲染

將 PDF 頁面轉成高解析圖片。

目前工具已有 render 指令：

```bash
.venv/bin/python pdf_zhuyin_audit.py render "/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf" --page 39 --output page39_2x.png --scale 2
```

後續 OCR 建議使用 2x 或 3x 解析度。注音很小，解析度太低會明顯影響辨識率。

### 3. OCR 中文與注音

需要 OCR 取得：

- 辨識出的中文字。
- 辨識出的注音符號。
- 每個字或每個小區塊的座標 bbox。
- OCR 信心分數。

目前電腦有安裝 `tesseract`：

```bash
tesseract --list-langs
```

但目前只有：

```text
eng
osd
snum
```

沒有繁中或注音可用語言包。下一步若使用 Tesseract，需要安裝或準備：

- `chi_tra`
- 可辨識注音符號的訓練資料，或自訂注音 OCR 模型。

實務上注音很小，Tesseract 不是最穩方案。下一位 Codex 可以評估：

- Google Cloud Vision OCR
- Azure AI Vision
- PaddleOCR 繁中模型
- EasyOCR
- Tesseract + 自訂注音訓練
- 自製注音分類器，優先推薦作為下一階段主線
- 版面固定時，針對注音區域做專門切割與辨識

第一版不必一次選最完美方案，重點是先能在第 22 頁抓到 `成為` 的 `為` 注音錯誤。

### 4. 中文與注音座標配對

OCR 後需要把中文和旁邊注音配對。資料結構建議長這樣：

```json
{
  "page": 39,
  "text": "蛤蠣",
  "text_boxes": [
    [100, 200, 120, 240],
    [121, 200, 141, 240]
  ],
  "zhuyin": "ㄍㄜˊ ㄌㄧˋ",
  "zhuyin_boxes": [
    [100, 180, 120, 199],
    [121, 180, 141, 199]
  ],
  "confidence": 0.86
}
```

配對規則需依版面確認。常見情境：

- 注音在中文字上方。
- 注音在中文字右側。
- 橫排文字搭配小注音。
- 直排文字搭配旁注。

這份範例截圖看起來是橫排文章，注音以小字標在中文字附近。實作時應從第 39 頁開始調配對規則，不要一開始就泛化到所有版型。

### 5. 產生疑慮候選

先用本地規則抓疑慮，不要直接查全部。

第一版建議規則：

1. 注音格式不合法。
   - 例如只出現聲調符號、缺少聲母或韻母、組合不可能。

2. 注音與中文字數量不一致。
   - 例如兩個中文字只配到一組注音。

3. OCR 信心太低。
   - OCR confidence 低於門檻時列為「需人工確認」。

4. 座標配對信心低。
   - 注音離中文字太遠、重疊到其他字、或同一注音可能對到多個字。

5. 本地字音表快速比對不通過。
   - 可先建立常用字/詞注音資料表。
   - 若 PDF 注音不在候選音中，列為疑慮。

6. 多音字與詞語優先。
   - 多音字不要直接判錯。
   - 優先用詞語查教育部，例如「蛤蠣」不要拆成「蛤」與「蠣」各自查。

### 6. 教育部查詢

目前工具已實作教育部查詢範例。

```bash
.venv/bin/python pdf_zhuyin_audit.py lookup 蛤蠣
```

目前實測輸出：

```json
{
  "word": "蛤蠣",
  "zhuyin": "ㄍㄜˊ ㄌㄧˋ",
  "source_url": "https://dict.revised.moe.edu.tw/search.jsp?md=1&word=%E8%9B%A4%E8%A0%A3",
  "title": "&lt; 蛤蠣 : ㄍㄜˊ ㄌㄧˋ &gt;辭典檢視 - 教育部《重編國語辭典修訂本》2021",
  "description": "字詞:蛤蠣,注音:ㄍㄜˊ　ㄌㄧˋ,釋義:蛤蜊的別名。參見「蛤蜊」條。",
  "ssl_fallback": true
}
```

注意：

- Python 3.14 對教育部網站憑證驗證較嚴格，目前程式在正常 SSL 驗證失敗時會 fallback 到 unverified SSL context。
- 這是原型做法。正式版本應改用更乾淨的 HTTP client、憑證處理或本地快取資料。
- 應加入查詢快取，避免同一個詞重複打教育部網站。

### 7. 輸出校稿報告

第一版建議輸出 CSV 和 JSON，不急著做 Web。

建議欄位：

```text
page
x
y
candidate_text
pdf_zhuyin
moe_zhuyin
status
reason
confidence
source_url
```

範例：

```text
page=39
candidate_text=蛤蠣
pdf_zhuyin=ㄍㄜˊ ㄌㄧˊ
moe_zhuyin=ㄍㄜˊ ㄌㄧˋ
status=suspected_error
reason=tone_mismatch
source_url=https://dict.revised.moe.edu.tw/search.jsp?md=1&word=%E8%9B%A4%E8%A0%A3
```

第二版再做 HTML 預覽或在頁面截圖上畫框。第三版再包成 Web App。

## 建議開發順序

### Milestone 1：先跑通第 39 頁單頁 OCR

目標：

- 把第 39 頁渲染成高解析圖片。
- OCR 出圈選附近的中文字與注音。
- 至少能人工或半自動定位到「蛤蠣」這類候選。
- 查教育部得到標準注音。
- 輸出一筆疑似錯誤紀錄。

不要一開始就做整份 PDF 或 Web UI。

### Milestone 2：單頁自動候選產生

目標：

- 自動取得第 39 頁所有中文/注音候選。
- 建立座標配對規則。
- 輸出第 39 頁疑慮清單。

### Milestone 3：整份 PDF 批次處理

目標：

- 對 44 頁逐頁處理。
- 加入查詢快取。
- 產生完整 CSV/JSON 報告。

### Milestone 4：可視化校稿

目標：

- 產生 HTML 報告。
- 顯示頁面圖片。
- 在疑似錯誤處畫框。
- 點擊項目時顯示 PDF 注音、教育部標準注音與來源連結。

### Milestone 5：Web App

目標：

- 上傳 PDF。
- 背景處理。
- 瀏覽器中檢視疑似錯誤。
- 讓老師標記「確認錯誤 / 誤判 / 忽略」。

## 目前專案檔案

```text
pdf_zhuyin_audit.py
requirements.txt
README.md
.gitignore
```

### `pdf_zhuyin_audit.py`

目前提供三個指令：

```bash
.venv/bin/python pdf_zhuyin_audit.py inspect PDF_PATH [--page PAGE]
.venv/bin/python pdf_zhuyin_audit.py render PDF_PATH --page PAGE --output OUTPUT.png [--scale 2]
.venv/bin/python pdf_zhuyin_audit.py lookup WORD
```

### `requirements.txt`

目前只有：

```text
PyMuPDF==1.27.2.3
Pillow==12.0.0
```

之後做 OCR 時再加入 OCR 套件或 API client。

### `.gitignore`

忽略：

```text
.venv/
*.png
__pycache__/
```

## 本地 setup

```bash
cd /Users/joneswang/Downloads/code/pdf_reader
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 已驗證指令

PDF 診斷：

```bash
.venv/bin/python pdf_zhuyin_audit.py inspect "/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf" --page 39
```

教育部查詢：

```bash
.venv/bin/python pdf_zhuyin_audit.py lookup 蛤蠣
```

Page 22 benchmark：

```bash
.venv/bin/python scripts/page22_benchmark.py
```

Page 22 區域擷取：

```bash
.venv/bin/python scripts/extract_page_regions.py page22_3x.png \
  --output-dir artifacts/page22_regions \
  --json-output artifacts/page22_regions.json \
  --padding 40
```

整份 PDF 型態統計：

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from pdf_zhuyin_audit import inspect_pdf

pdf = Path('/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf')
rows = inspect_pdf(pdf)
print('pages', len(rows))
print('extractable_pages', sum(1 for row in rows if row['is_extractable_text']))
print('image_only_pages', sum(1 for row in rows if row['images'] and not row['is_extractable_text']))
PY
```

目前結果：

```text
pages 44
extractable_pages 0
image_only_pages 44
```

## 給下一位 Codex 的接手重點

請不要從 Web App 開始，也不要一開始訓練完整 OCR。這個專案第一個真正風險是「能不能穩定讀出小注音」，尤其是第 22 頁 `成為` 的 `為`。

請先做：

1. 跑 `scripts/page22_benchmark.py`。
2. 檢查 `artifacts/page22_benchmark/results.json`。
3. 確認 crop 中的 `為` 旁邊注音是否清楚保留。
4. 比較 Tesseract / Apple Vision / 其他 OCR 的輸出。
5. 若現成 OCR 無法輸出 `ㄨㄟˊ` 或 `ㄨㄟˋ`，再進入注音專用分類器。
6. 先讓第 22 頁 `成為` 成為第一個穩定 regression target。

成功標準：

- 能穩定切出第 22 頁 `成為` crop。
- 能讀出或明確證明現成 OCR 讀不出 `為` 的 PDF 實際注音。
- 能產生 benchmark JSON，記錄方法、crop、輸出與失敗原因。
- 若進入訓練，訓練目標只限注音符號/聲調，不做整頁 OCR 大模型。

若 benchmark 證明現成 OCR 無法穩定辨識注音，下一步不要硬做全自動；請改成注音專用流程：

- 自動渲染頁面。
- 自動或手動找出注音 crop。
- 建立小型標註資料集。
- 訓練或模板比對注音符號。
- 再接教育部查詢與比對報告。

這樣仍然能大幅減少老師查字典的時間。
