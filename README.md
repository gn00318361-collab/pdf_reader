# Single PDF Zhuyin Review

This repo is now focused on one job: review the 44 pages in `sample.pdf` for
possible printed Zhuyin/Bopomofo mistakes.

The first goal is not perfect OCR. The first goal is a fast proofreading
workspace:

```text
sample.pdf
-> rendered page images
-> line/region boxes around text plus nearby zhuyin
-> crop images
-> static review UI
-> exported human review notes
```

The UI is manual-first. Automatic boxes are only rough suggestions. For actual
proofreading, use `Draw box` in the review page to draw a region that contains
the large text plus its nearby printed zhuyin.

## Files

```text
sample.pdf                         source PDF
requirements.txt                   Python dependencies
scripts/build_single_pdf_review.py repeatable build command
artifacts/full_audit/review.html   generated review UI
```

## Build

```powershell
python scripts/build_single_pdf_review.py --pdf sample.pdf --output artifacts/full_audit
```

The command creates:

```text
artifacts/full_audit/pages/
artifacts/full_audit/crops/
artifacts/full_audit/overlays/
artifacts/full_audit/candidates.csv
artifacts/full_audit/candidates.json
artifacts/full_audit/review.html
```

Open `artifacts/full_audit/review.html` in a browser.

Review notes and manually drawn boxes are stored in browser `localStorage`.
Use `Export JSON` to download the current review state.

## Review Policy

Keep these separate:

```text
printed_zhuyin  = what the PDF visibly prints
expected_zhuyin = the standard pronunciation from a trusted source
```

Model output, including LM Studio/Gemma, should only rank or triage candidates.
Do not accept model output as final proofreading truth without checking the crop.

If LM Studio has a vision-capable Gemma 4B loaded, it can be added later as a
batch reviewer for the drawn crops. If the loaded model is text-only, it cannot
inspect the crop images.
