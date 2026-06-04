# Page 22 Smoke Test

PDF:

```text
sample.pdf
```

Rendered page image:

```text
/Users/joneswang/Downloads/code/pdf_reader/page22_3x.png
```

## PDF Layer Check

Command:

```bash
.venv/bin/python pdf_zhuyin_audit.py inspect sample.pdf --page 22
```

Result:

```json
[
  {
    "page": 22,
    "text_chars": 0,
    "zhuyin_chars": 0,
    "images": 1,
    "fonts": 0,
    "is_extractable_text": false
  }
]
```

Conclusion: page 22 is image-only and requires OCR.

## OCR Attempts

### Tesseract

Installed `chi_tra.traineddata` and ran Tesseract on the 3x page render.

Result:

- It can detect some large Chinese characters.
- It does not reliably detect zhuyin.
- It frequently turns zhuyin marks into `#`, `*`, digits, or Latin letters.

Example noisy output:

```text
容是易一感台到公挫喜折告
擔心吉他 人只眼 光炎
```

Conclusion: general Tesseract with `chi_tra` is not enough for this document's small zhuyin.

### Apple Vision OCR

Added:

```text
scripts/vision_ocr.swift
```

Command:

```bash
swift scripts/vision_ocr.swift page22_3x.png
```

Result:

- Apple Vision detects a few large Chinese text lines.
- It still fails to preserve zhuyin accurately.
- Confidence is low for most content once zhuyin is mixed into the line.

Example output:

```text
0.30 容是易一感台到公挫喜折告
0.30 擔心吉他 人只眼 光炎
0.30 我們！的？理”解與v接呈納，對他 們！來
```

Conclusion: Apple Vision is useful as a quick local OCR sanity check, but not sufficient for full zhuyin verification.

## Known Ground Truth

The user later clarified that the real known issue on page 22 is not `心理方面`.

Correct target:

```text
Page: 22
Phrase: 成為
Problem character: 為
Expected phrase zhuyin: ㄔㄥˊ ㄨㄟˊ
Issue: the printed zhuyin for 為 is wrong
```

This is the first regression target for the project. Future work should treat
`成為` as the known positive case and should not optimize for the earlier
`心理方面` guess.

## Manual Visual Check

The page was rendered at 3x and cropped/zoomed for visual inspection.

Useful crop files generated during the test:

```text
debug_crops/page22_title_zoom.png
debug_crops/page22_title_xinlifangmian_zoom.png
debug_crops/page22_traits_zoom.png
```

Earlier incorrect candidate:

```text
Page: 22
Area: title line
Text: 心理方面
Suspicious character: 面
Expected MOE zhuyin: ㄇㄧㄢˋ
Suspicion: the printed tone mark beside 面 appears inconsistent with fourth tone.
Status: suspected, needs confirmation by better zhuyin OCR or human review.
```

This was a wrong target. It is retained here only as evidence that visual/manual
inspection and general OCR are not reliable enough for this task.

Related MOE URL:

```text
https://dict.revised.moe.edu.tw/dictView.jsp?ID=36075&word=%E6%96%B9%E9%9D%A2
```

MOE entry for `方面` shows:

```text
方面：ㄈㄤ ㄇㄧㄢˋ
```

## Current Result

This page 22 test did not produce a fully automatic detection yet.

It did produce a useful engineering result:

1. The PDF has no text layer.
2. Local general-purpose OCR cannot reliably read the small zhuyin.
3. The actual known issue is `成為` / `為`, not the earlier `心理方面` guess.
4. Page 22 should become the first regression target for the real OCR/zhuyin pipeline.

## Region Extraction Result

Added:

```text
scripts/extract_page_regions.py
```

Purpose:

```text
Render page image
-> use OCR only to find rough text-line regions
-> crop visual regions that contain both Chinese text and nearby zhuyin
-> save JSON metadata and PNG crops
```

This does not solve zhuyin recognition yet. It creates the data needed for the
next step: training a zhuyin-specific classifier.

Command:

```bash
.venv/bin/python scripts/extract_page_regions.py page22_3x.png \
  --output-dir artifacts/page22_regions \
  --json-output artifacts/page22_regions.json \
  --padding 40
```

Observed output:

```text
regions=32
```

The line containing the known issue was extracted:

```text
artifacts/page22_regions/region_335_line_23.png
```

Tesseract noisy text for that line:

```text
@ 成 為 * 溫 * 暖 1 的 # 小 # 幫 : 手 人
```

Important interpretation:

- The OCR can roughly find the line and the text `成 為`.
- The zhuyin is not recognized as zhuyin. It appears as `*`, `1`, `#`, `:`, etc.
- Therefore the next step must be a zhuyin-specific classifier, not another pass of generic OCR.

Focused crop for weekend research:

```text
artifacts/page22_regions/target_chengwei.png
```

This crop should be used to test whether the project can identify the zhuyin
beside `為` and compare it with the expected `ㄨㄟˊ`.

## Recommended Next Step

Do not continue with plain Tesseract or Apple Vision as the final OCR engine.

Next implementation should switch to a zhuyin-specific OCR/classifier path:

1. Render page 22 at 3x or 4x.
2. Segment text lines and zhuyin regions separately.
3. Build a labeled dataset of cropped zhuyin glyphs.
4. Train or prototype:
   - template matching for this PDF/font
   - small CNN classifier for zhuyin symbols and tone marks
5. Use `成為` as the known target:
   - expected: `ㄔㄥˊ ㄨㄟˊ`
   - target character: `為`
6. Emit a report row only when the classifier confidence for the zhuyin mark is high enough.

Expected report row shape:

```json
{
  "page": 22,
  "candidate_text": "成為",
  "pdf_zhuyin": "ㄔㄥˊ ㄨㄟˋ",
  "moe_zhuyin": "ㄔㄥˊ ㄨㄟˊ",
  "status": "suspected_error",
  "reason": "tone_mismatch_on_為"
}
```
