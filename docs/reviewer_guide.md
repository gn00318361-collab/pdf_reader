# 審核者指南

這份 repo 的審核目標是人工確認 473 筆多音字/破音字 review candidates。系統只提供理論正確讀音與截圖，不自動判斷 PDF 上印出的注音是否真的錯。

## 開啟 Dashboard

第一次拿到 repo 後，可以直接開啟：

```text
outputs/review/index.html
```

或用本機 server：

```powershell
python -m http.server 8765 --bind 127.0.0.1 --directory outputs
```

然後瀏覽：

```text
http://127.0.0.1:8765/review/
```

## 重新產生 Dashboard

只有想重新跑 OCR / 候選 / dashboard 時才需要：

```powershell
pip install -r requirements.txt
python src\run_review_pipeline.py --gpu
```

如果已經有 `outputs/ocr/*.json`，只要重建候選與 dashboard：

```powershell
python src\run_review_pipeline.py --skip-ocr
```

目前 repo 已提交靜態 dashboard、詞級 crop、annotated page WebP，所以單純審核不需要先重跑 pipeline。

## 審核順序

1. 先用狀態篩選 `semantic_unresolved`，處理最不確定的 23 筆。
2. 再用優先級篩選 `high`。
3. 看 crop，如果不清楚就點 `annotated` 開原頁標記圖。
4. 沒問題勾 `✓`，該列會進 Checked / OK。
5. 有注音錯或需要修正勾 `!`，該列會進 Issues。

## 交接標記

標記會先存在瀏覽器 localStorage。要交接給別人：

1. 在 dashboard 按 `匯出標記`。
2. 把下載的 JSON 內容更新到 `data/review_state.json`。
3. commit/push。

對方可直接讀 `data/review_state.json`，或在 dashboard 按 `匯入標記` 載回狀態。
