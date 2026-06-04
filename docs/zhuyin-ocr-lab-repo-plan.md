# Zhuyin OCR Lab Repo Plan

Recommended private repo name:

```text
zhuyin-ocr-lab
```

Recommended GitHub description:

```text
Synthetic data generation and model training experiments for recognizing printed Bopomofo/Zhuyin crops in Taiwanese educational PDFs.
```

## Why Separate Repo

This current repo is for:

```text
PDF inspection
page rendering
real crop extraction
page22 benchmark
annotation CSV
eventual proofreading pipeline
```

The new repo should be for:

```text
synthetic data generation
OCR/recognizer training
model checkpoints
Windows + RTX 5080 setup
experiment tracking
```

Keeping them separate avoids mixing large generated datasets and model weights
with the PDF proofreading pipeline.

## Role of esun-ai/bopomofo

`esun-ai/bopomofo` is useful as a pronunciation/annotation generator, not as an
image OCR model.

Use it for:

```text
Chinese text -> expected zhuyin
```

Then render the annotated text into images:

```text
Chinese + zhuyin
-> right-side vertical zhuyin layout
-> synthetic crop image
-> label CSV / metadata JSON
```

Important: check LGPL 2.1 obligations before commercial use or product bundling.

## Training Target

Do not train a full-page OCR model first.

First training task:

```text
single-character crop with nearby printed zhuyin -> printed_zhuyin
```

Example:

```json
{
  "crop_id": "p22_wei_001",
  "char": "為",
  "word_context": "成為",
  "printed_zhuyin": "ㄨㄟˋ",
  "expected_zhuyin": "ㄨㄟˊ",
  "status": "error"
}
```

The recognizer learns `printed_zhuyin`. The proofreading pipeline compares that
against `expected_zhuyin`.

## First Milestone

1. Build a synthetic dataset generator.
2. Render single-character crops with right-side vertical zhuyin.
3. Add degradation transforms:
   - blur
   - JPEG/PNG compression
   - small rotations
   - scaling
   - background color/noise
   - font variation
4. Generate `labels.csv` and `metadata.json`.
5. Include real crops from this repo:
   - `p22_cheng_001`
   - `p22_wei_001`
   - `p22_wen_001`
   - `p22_nuan_001`
6. Train a small baseline classifier.
7. Confirm train/val runs on Windows with RTX 5080.

## Suggested Repo Structure

```text
zhuyin-ocr-lab/
  README.md
  pyproject.toml
  configs/
    synthetic.yaml
    train_classifier.yaml
  src/
    zhuyin_ocr_lab/
      synth/
        render_html.py
        generate_dataset.py
      data/
        dataset.py
        transforms.py
      models/
        classifier.py
      train.py
      eval.py
      infer.py
  dataset/
    synthetic/
    real/
    labels/
  artifacts/
    runs/
    checkpoints/
  docs/
    windows-5080-setup.md
    synthetic-data-plan.md
```

## Windows 5080 Setup Goal

The first Windows goal is not high accuracy. It is just:

```text
Can the repo run one complete train/val loop on the RTX 5080?
```

Minimum command target:

```bash
python -m zhuyin_ocr_lab.synth.generate_dataset --config configs/synthetic.yaml
python -m zhuyin_ocr_lab.train --config configs/train_classifier.yaml
python -m zhuyin_ocr_lab.eval --checkpoint artifacts/runs/latest/best.pt
```

## Connection Back to This Repo

This current repo provides real crops and benchmark cases.

The lab repo should export:

```text
model checkpoint
label vocabulary
inference script or ONNX model
metrics JSON
```

Then this repo can consume it inside the proofreading pipeline:

```text
PDF crop -> zhuyin model -> printed_zhuyin -> compare with expected_zhuyin
```
