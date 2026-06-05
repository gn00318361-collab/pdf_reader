# Single-PDF Zhuyin Audit Handoff

This handoff is for a new session focused on `pdf_reader`, not
`zhuyin-ocr-lab`.

## Current Decision

For the immediate user goal, stop optimizing the general OCR training track and
focus on this one concrete PDF:

```text
C:\Users\jones\Downloads\code\pdf_reader\sample.pdf
```

The user wants to find possible printed Zhuyin/Bopomofo mistakes in this
44-page school publication as efficiently as possible. Generalization to other
PDF formats is secondary.

## Repo Responsibility Split

`pdf_reader` should own the short-term product workflow:

```text
PDF render
page / region / line / crop extraction
crop QA overlays
review HTML
manual correction workflow
optional local model batch review
final suspicious-error report
```

`zhuyin-ocr-lab` should remain the longer-term model lab:

```text
synthetic data generation
ruby-only recognizer training
tone confusion benchmark
checkpoints / metrics / inference API
```

Do not spend the next session debugging model training first unless it directly
unblocks this 44-page PDF audit.

## What We Learned

1. `sample.pdf` is image-only.
   Earlier inspection showed:

   ```text
   pages: 44
   extractable_pages: 0
   image_only_pages: 44
   ```

2. Generic OCR is not reliable for the tiny printed zhuyin.
   Tesseract and Apple Vision can see large Chinese characters but often lose
   or mangle the small zhuyin/tone marks.

3. Page 22 is only one case, not the whole task.
   The known target is the word usually romanized here as `cheng-wei`.
   The target character is `wei`.

   ```text
   page: 22
   word_context: cheng-wei
   target_char: wei
   expected_zhuyin: wei, tone 2
   suspected printed issue: wei, tone 4
   ```

4. Crop quality is a first-class problem.
   Some page 22 crops looked suspicious only because the crop box was wrong or
   clipped. Do not treat every bad crop as a pronunciation error.

5. Tone placement matters.
   The PDF places tone marks on the right side of the vertical zhuyin body.
   Distinguishing tone 2 versus tone 4 is especially important. Tone 3 and
   neutral tone are usually easier visually, but still need crop quality checks.

## Recommended Next Task

Build a single-PDF brute-force review mode in `pdf_reader`.

Minimum useful pipeline:

```text
sample.pdf
-> render all 44 pages at high scale
-> segment candidate text/zhuyin regions
-> create line/region crops
-> generate crop QA overlays
-> generate review HTML
-> optionally run local model/VLM overnight for candidate ranking
-> output suspicious list for human review
```

The first deliverable should be review infrastructure, not perfect OCR.

## Suggested Implementation Plan

### 1. Render And Inventory

Render all 44 pages into:

```text
artifacts/full_audit/pages/page_001.png
...
artifacts/full_audit/pages/page_044.png
```

Create a page inventory JSON:

```json
{
  "page": 22,
  "page_image": "artifacts/full_audit/pages/page_022.png",
  "candidate_regions": []
}
```

### 2. Candidate Region Extraction

For the first pass, do not aim for perfect per-character boxes. Extract larger
reviewable units:

```text
page region
text block
line crop
```

Use image processing heuristics:

```text
grayscale
threshold dark pixels
connected components
horizontal projection for lines
merge close boxes
filter tiny noise and decorative blocks
```

Save:

```text
artifacts/full_audit/regions/
artifacts/full_audit/lines/
artifacts/full_audit/overlays/
artifacts/full_audit/candidates.csv
artifacts/full_audit/candidates.json
```

### 3. Review HTML

Generate a static HTML review page:

```text
artifacts/full_audit/review.html
```

Each card should show:

```text
page number
region/line id
crop image
overlay image
fields:
  suspected_error: yes/no/uncertain
  printed_zhuyin
  expected_zhuyin
  note
  crop_quality: good/weak/bad
```

The purpose is to reduce the human review surface from 44 pages to a list of
candidate crops.

### 4. Optional Local Model Overnight

If the user has a local Gemma 4B:

```text
If it is text-only:
  use it only on OCR text or human-entered text; it cannot inspect crops.

If it is vision-capable:
  batch-feed crop images and ask for candidate ranking, not final truth.
```

Recommended VLM prompt style:

```text
You are reviewing a crop from a Taiwanese school publication.
Look only for suspicious printed Zhuyin/Bopomofo issues.
Return JSON with:
  readable: true/false
  suspected_error: true/false/uncertain
  printed_zhuyin_if_visible
  reason
```

Important: model output should only prioritize human review. It should not be
accepted as final proofreading truth.

### 5. Page 22 Regression Target

Keep page 22 `cheng-wei / wei` as a regression case.

Expected output for the final tool:

```text
page: 22
location: bbox around target `wei`
printed_zhuyin: wei, tone 4, if confirmed by human
expected_zhuyin: wei, tone 2
status: suspected_error / confirmed_error
```

## Existing Useful Files

Current repo files likely useful:

```text
pdf_zhuyin_audit.py
scripts/page22_benchmark.py
scripts/extract_page_regions.py
scripts/prepare_page22_dataset.py
dataset/labels/zhuyin_labels.csv
dataset/metadata/crops.json
artifacts/page22_regions/target_chengwei.png
```

`zhuyin-ocr-lab` has useful longer-term assets but should not block this
single-PDF audit:

```text
synthetic ruby-only generator
tone benchmark
ruby_core baseline checkpoint
real page22 import/annotation scaffold
```

## Success Criteria For The Next Session

A good first session in `pdf_reader` should produce:

```text
artifacts/full_audit/review.html
artifacts/full_audit/candidates.csv
artifacts/full_audit/overlays/
```

and a repeatable command, for example:

```powershell
python scripts/full_pdf_zhuyin_audit.py --pdf sample.pdf --output artifacts/full_audit
```

Do not promise full automatic correctness yet. The immediate win is making the
44-page proofreading task reviewable and traceable.
