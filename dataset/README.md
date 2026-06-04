# Zhuyin Crop Dataset

This folder stores crop images and labels for the zhuyin recognizer.

The task is not to predict the correct dictionary pronunciation directly.
The recognizer must read what is printed in the PDF.

Keep these fields separate:

```text
printed_zhuyin = the zhuyin actually printed in the PDF crop
expected_zhuyin = the standard pronunciation from MOE or another trusted source
```

For example, page 22 has a known issue:

```text
word_context: 成為
char: 為
expected_zhuyin: ㄨㄟˊ
printed_zhuyin: fill manually after inspecting the crop
status: error once confirmed
```

## Folders

```text
zhuyin_crops/raw/        original extracted crop images
zhuyin_crops/processed/  enlarged/sharpened/binary variants
zhuyin_crops/labeled/    optional curated copies after review
labels/                  CSV label files for annotation and training
metadata/                JSON metadata for each crop
splits/                  train/val/test CSV files later
```

Current crop images intentionally include the large Chinese character and its
nearby zhuyin. This supports the first practical model direction:

```text
single-character crop with nearby zhuyin -> printed_zhuyin
```

## Manual Annotation

Open:

```text
dataset/labels/zhuyin_labels.csv
```

Fill these columns:

```text
printed_zhuyin
label_status
status
notes
```

Recommended values:

```text
label_status: unlabeled | labeled | uncertain
status: unknown | correct | error | uncertain
```

Do not change `expected_zhuyin` unless the standard pronunciation source changes.
