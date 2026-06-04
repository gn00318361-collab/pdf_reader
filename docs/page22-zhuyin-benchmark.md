# Page 22 Zhuyin Benchmark

This benchmark is the next correct step before training any model.

## Target

```text
PDF: sample.pdf
Page: 22
Target word: 成為
Expected standard zhuyin: ㄔㄥˊ ㄨㄟˊ
Known issue: 為 has the wrong printed zhuyin/tone in the PDF
```

The goal is not to solve the whole PDF yet. The first success condition is:

```text
Given a crop around 成為, can any current method read the printed zhuyin beside 為?
```

## Why Benchmark First

Do not train a full OCR model first. The project needs to know where the failure
actually happens:

- crop region is wrong
- zhuyin is too small
- preprocessing loses the tone mark
- generic OCR cannot recognize zhuyin
- only the tone mark fails

The benchmark records crop images and OCR outputs so these failures are visible.

## Script

```bash
.venv/bin/python scripts/page22_benchmark.py
```

It creates:

```text
artifacts/page22_benchmark/results.json
artifacts/page22_benchmark/scale_3/page22.png
artifacts/page22_benchmark/scale_3/target_chengwei_raw.png
artifacts/page22_benchmark/scale_3/target_chengwei_enlarged.png
artifacts/page22_benchmark/scale_3/target_chengwei_sharp.png
artifacts/page22_benchmark/scale_3/target_chengwei_binary.png
```

The script repeats the same process for scale 3, 4, and 5 by default.

## Baseline OCR Methods

Current baseline methods:

- Tesseract `chi_tra`, `--psm 7`
- Apple Vision OCR via `scripts/vision_ocr.swift`

Expected first benchmark result:

```text
Generic OCR will probably read 成為 as text but fail to return reliable zhuyin.
```

Observed baseline result from the first run:

```text
scale 3, Tesseract: @> 成 / 為 * 溫 * 暖 ;
scale 4, Tesseract: @> 成 / 為 * 溫 暖
scale 3, Apple Vision: 成 為 溫 暖
```

Interpretation:

- Existing OCR can see the large Chinese characters.
- Existing OCR does not return usable zhuyin.
- The zhuyin beside `為` is effectively lost or converted to punctuation-like symbols such as `*`.
- This confirms the next useful work is better zhuyin crop segmentation and a zhuyin-specific recognizer, not another full-page OCR pass.

If all baseline methods fail, the next step is not another full-page OCR pass.
The next step is a zhuyin-specific recognizer:

```text
crop around one character's zhuyin
-> classify ㄨ / ㄟ / ˊ / ˋ / ...
-> assemble ㄨㄟˊ or ㄨㄟˋ
-> compare against 成為 = ㄔㄥˊ ㄨㄟˊ
```

## Expected Result Schema

```json
{
  "page": 22,
  "target_word": "成為",
  "expected_standard_zhuyin": "ㄔㄥˊ ㄨㄟˊ",
  "known_issue": "tone mismatch on 為",
  "runs": [
    {
      "scale": 3,
      "page_image": "artifacts/page22_benchmark/scale_3/page22.png",
      "crops": {
        "raw": "artifacts/page22_benchmark/scale_3/target_chengwei_raw.png"
      },
      "ocr_results": [
        {
          "method": "tesseract_chi_tra_psm7",
          "stdout": "..."
        }
      ]
    }
  ]
}
```

## Decision Rule

Proceed to zhuyin model training only if:

```text
1. crop contains the relevant zhuyin clearly
2. preprocessing variants preserve the tone mark
3. baseline OCR still cannot produce ㄨㄟˊ / ㄨㄟˋ reliably
```

If baseline OCR does work on a crop, use that first and defer model training.
