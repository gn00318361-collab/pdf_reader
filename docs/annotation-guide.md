# Annotation Guide

The next manual task is to label what is actually printed in each zhuyin crop.

Open:

```text
dataset/zhuyin_crops/contact_sheet_page22.png
dataset/labels/zhuyin_labels.csv
```

For each row in `zhuyin_labels.csv`, fill:

```text
printed_zhuyin
label_status
status
notes
```

## Important Rule

Do not copy `expected_zhuyin` into `printed_zhuyin` unless the crop actually
prints the same zhuyin.

Definitions:

```text
printed_zhuyin = what the PDF visibly prints
expected_zhuyin = the standard/correct pronunciation
```

The OCR model should learn `printed_zhuyin`, not `expected_zhuyin`.

## Page 22 First Samples

The first generated crops are:

```text
p22_cheng_001  成 in 成為  expected ㄔㄥˊ
p22_wei_001    為 in 成為  expected ㄨㄟˊ  known issue target
p22_wen_001    溫 in 溫暖  expected ㄨㄣ
p22_nuan_001   暖 in 溫暖  expected ㄋㄨㄢˇ
```

For `p22_wei_001`, inspect the crop and write what is actually printed beside
`為`. If the crop is not clear enough, set:

```text
printed_zhuyin=
label_status=uncertain
status=uncertain
notes=need wider or sharper crop
```

If it clearly prints the wrong tone, fill for example:

```text
printed_zhuyin=ㄨㄟˋ
label_status=labeled
status=error
notes=printed tone differs from expected ㄨㄟˊ
```

For correct examples:

```text
printed_zhuyin=ㄔㄥˊ
label_status=labeled
status=correct
notes=
```

## CSV Columns

```text
crop_id
page
char
word_context
crop_path
processed_crop_path
crop_bbox
text_bbox
zhuyin_bbox
render_scale
expected_zhuyin
printed_zhuyin
label_status
status
known_printed_issue
notes
```

Recommended values:

```text
label_status: unlabeled | labeled | uncertain
status: unknown | correct | error | uncertain
```
