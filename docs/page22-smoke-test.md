# Page 22 Smoke Test

PDF:

```text
/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf
```

Rendered page image:

```text
/Users/joneswang/Downloads/code/pdf_reader/page22_3x.png
```

## PDF Layer Check

Command:

```bash
.venv/bin/python pdf_zhuyin_audit.py inspect "/Users/joneswang/Downloads/青溪校刊-最終校稿（六年級更正版）.pdf" --page 22
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

## Manual Visual Check

The page was rendered at 3x and cropped/zoomed for visual inspection.

Useful crop files generated during the test:

```text
debug_crops/page22_title_zoom.png
debug_crops/page22_title_xinlifangmian_zoom.png
debug_crops/page22_traits_zoom.png
```

Observed candidate issue:

```text
Page: 22
Area: title line
Text: 心理方面
Suspicious character: 面
Expected MOE zhuyin: ㄇㄧㄢˋ
Suspicion: the printed tone mark beside 面 appears inconsistent with fourth tone.
Status: suspected, needs confirmation by better zhuyin OCR or human review.
```

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
3. The likely known issue can be narrowed visually to the title phrase `心理方面`, especially the tone on `面`.
4. Page 22 should become the first regression target for the real OCR/zhuyin pipeline.

## Recommended Next Step

Do not continue with plain Tesseract or Apple Vision as the final OCR engine.

Next implementation should test a stronger OCR path against page 22:

1. Render page 22 at 3x or 4x.
2. Segment text lines and zhuyin regions separately.
3. Try OCR with one of:
   - Google Cloud Vision
   - Azure AI Vision
   - PaddleOCR with a Traditional Chinese model
   - a custom zhuyin classifier for cropped annotation glyphs
4. Use `心理方面` as a known target:
   - expected: `ㄒㄧㄣ ㄌㄧˇ ㄈㄤ ㄇㄧㄢˋ`
   - candidate mismatch: tone on `面`
5. Emit a report row only when the OCR confidence for the zhuyin mark is high enough.

Expected report row shape:

```json
{
  "page": 22,
  "candidate_text": "心理方面",
  "pdf_zhuyin": "ㄒㄧㄣ ㄌㄧˇ ㄈㄤ ㄇㄧㄢ?",
  "moe_zhuyin": "ㄒㄧㄣ ㄌㄧˇ ㄈㄤ ㄇㄧㄢˋ",
  "status": "suspected_error",
  "reason": "tone_mismatch_on_面",
  "source_url": "https://dict.revised.moe.edu.tw/dictView.jsp?ID=36075&word=%E6%96%B9%E9%9D%A2"
}
```
