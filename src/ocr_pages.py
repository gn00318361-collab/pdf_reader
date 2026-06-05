from __future__ import annotations

import argparse
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from pipeline_common import (
    RISK_TERMS_PATH,
    annotated_image_path,
    ensure_dirs,
    find_matches,
    page_image_path,
    page_ocr_path,
    parse_pages,
    read_json,
    write_json,
)
from gpu_runtime import preload_onnxruntime_cuda


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def normalize_box(raw_box: Any) -> list[list[float]]:
    return [[float(point[0]), float(point[1])] for point in raw_box]


def paddle_result_to_items(result: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    # PaddleOCR 2.x style: [[box, (text, confidence)], ...]
    if isinstance(result, list) and result and isinstance(result[0], list):
        candidate = result[0] if result and result[0] and isinstance(result[0][0], list) else result
        for row in candidate:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            box, payload = row[0], row[1]
            if isinstance(payload, (list, tuple)) and len(payload) >= 2:
                text, confidence = payload[0], payload[1]
            else:
                continue
            if text:
                items.append(
                    {
                        "text": str(text),
                        "confidence": float(confidence),
                        "box": normalize_box(box),
                    }
                )
        if items:
            return items

    # PaddleOCR 3.x predict style: dicts with rec_texts/rec_scores/rec_polys.
    records = result if isinstance(result, list) else [result]
    for record in records:
        if not isinstance(record, dict):
            continue
        texts = record.get("rec_texts") or []
        scores = record.get("rec_scores") or []
        boxes = record.get("rec_polys") or record.get("dt_polys") or record.get("rec_boxes") or []
        for index, text in enumerate(texts):
            if not text:
                continue
            box = boxes[index] if index < len(boxes) else []
            score = scores[index] if index < len(scores) else None
            items.append(
                {
                    "text": str(text),
                    "confidence": float(score) if score is not None else None,
                    "box": normalize_box(box) if len(box) else [],
                }
            )
    return items


def rapid_result_to_items(result: Any) -> list[dict[str, Any]]:
    boxes = getattr(result, "boxes", None)
    texts = getattr(result, "txts", None) or []
    scores = getattr(result, "scores", None) or []
    if boxes is None:
        boxes = []
    items: list[dict[str, Any]] = []

    for index, text in enumerate(texts):
        if not text:
            continue
        box = boxes[index] if index < len(boxes) else []
        score = scores[index] if index < len(scores) else None
        items.append(
            {
                "text": str(text),
                "confidence": float(score) if score is not None else None,
                "box": normalize_box(box) if len(box) else [],
            }
        )
    return items


def build_ocr_engine(use_gpu: bool):
    # Paddle 3.x CPU builds can hit oneDNN runtime conversion issues on some
    # Windows setups. Disabling it keeps the MVP path more predictable.
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")

    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError(
            "PaddleOCR is not installed. Install requirements first, then rerun OCR."
        ) from exc

    modern_kwargs = {
        "lang": "ch",
        "use_textline_orientation": True,
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "PP-OCRv5_mobile_rec",
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
    }
    if use_gpu:
        try:
            return PaddleOCR(device="gpu:0", **modern_kwargs)
        except Exception as exc:
            print(f"GPU PaddleOCR init failed, falling back to CPU: {exc}")
    try:
        return PaddleOCR(**modern_kwargs)
    except TypeError:
        # PaddleOCR 2.x compatibility.
        return PaddleOCR(lang="ch", use_angle_cls=True, show_log=False, use_gpu=use_gpu)


def build_rapid_engine(use_gpu: bool):
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:
        raise RuntimeError("RapidOCR is not installed. Install requirements first.") from exc

    params: dict[str, Any] = {
        "Global.log_level": "warning",
    }
    if use_gpu:
        ok, message = preload_onnxruntime_cuda()
        print(message)
        if not ok:
            print("RapidOCR GPU preload failed; ONNXRuntime may fall back to CPU.")
        params.update(
            {
                "EngineConfig.onnxruntime.use_cuda": True,
                "EngineConfig.onnxruntime.cuda_ep_cfg.device_id": 0,
                "EngineConfig.onnxruntime.cuda_ep_cfg.arena_extend_strategy": "kNextPowerOfTwo",
                "EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_algo_search": "EXHAUSTIVE",
                "EngineConfig.onnxruntime.cuda_ep_cfg.do_copy_in_default_stream": True,
            }
        )
    return RapidOCR(params=params)


def run_paddle_ocr(ocr: Any, image_path: str) -> Any:
    if hasattr(ocr, "ocr"):
        try:
            return ocr.ocr(image_path)
        except TypeError:
            return ocr.ocr(image_path, cls=True)
    if hasattr(ocr, "predict"):
        return ocr.predict(image_path)
    raise RuntimeError("Unsupported PaddleOCR object: missing ocr/predict method.")


def build_ocr_runner(engine: str, use_gpu: bool):
    if engine in {"paddle", "auto"}:
        try:
            paddle_ocr = build_ocr_engine(use_gpu=use_gpu)
            return "paddle", lambda image_path: paddle_result_to_items(run_paddle_ocr(paddle_ocr, image_path))
        except Exception as exc:
            if engine == "paddle":
                raise
            print(f"PaddleOCR failed, falling back to RapidOCR: {exc}")

    rapid_ocr = build_rapid_engine(use_gpu=use_gpu)
    return "rapidocr", lambda image_path: rapid_result_to_items(rapid_ocr(image_path))


def draw_overlay(page: int, items: list[dict[str, Any]]) -> None:
    image_path = page_image_path(page)
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(max(18, image.width // 120))

    for item in items:
        box = item.get("box") or []
        if len(box) < 4:
            continue
        token_id = item["token_id"]
        matched = bool(item.get("matched_risk_terms"))
        fill = (255, 106, 0, 80) if matched else (44, 177, 94, 55)
        outline = (230, 76, 0, 230) if matched else (25, 135, 84, 210)
        label_bg = (230, 76, 0, 235) if matched else (25, 135, 84, 235)

        polygon = [(point[0], point[1]) for point in box]
        draw.polygon(polygon, fill=fill, outline=outline)

        min_x = min(point[0] for point in box)
        min_y = min(point[1] for point in box)
        label = token_id
        label_bbox = draw.textbbox((min_x, min_y), label, font=font)
        padding = 4
        bg_box = [
            label_bbox[0] - padding,
            label_bbox[1] - padding,
            label_bbox[2] + padding,
            label_bbox[3] + padding,
        ]
        draw.rectangle(bg_box, fill=label_bg)
        draw.text((min_x, min_y), label, fill=(255, 255, 255, 255), font=font)

    annotated = Image.alpha_composite(image, overlay).convert("RGB")
    out_path = annotated_image_path(page)
    annotated.save(out_path, quality=95)
    print(f"annotated page {page} -> {out_path}")


def ocr_pages(pages: list[int], use_gpu: bool, engine: str) -> list[str]:
    ensure_dirs()
    risk_terms = read_json(RISK_TERMS_PATH)
    engine_used, ocr_runner = build_ocr_runner(engine, use_gpu)
    written: list[str] = []

    for page in pages:
        image_path = page_image_path(page)
        if not image_path.exists():
            raise FileNotFoundError(f"Missing rendered page image: {image_path}")

        items = ocr_runner(str(image_path))
        for index, item in enumerate(items, start=1):
            item["token_id"] = f"T{index:03d}"
            item["matched_risk_terms"] = find_matches(item["text"], risk_terms)

        page_text = "\n".join(item["text"] for item in items)
        payload = {
            "page": page,
            "ocr_engine": engine_used,
            "image": str(image_path),
            "annotated_image": str(annotated_image_path(page)),
            "text": page_text,
            "items": items,
        }
        out_path = page_ocr_path(page)
        write_json(out_path, payload)
        draw_overlay(page, items)
        written.append(str(out_path))
        print(f"ocr page {page} with {engine_used}: {len(items)} regions -> {out_path}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR rendered pages and generate annotated overlays.")
    parser.add_argument("--pages", default="22", help="Comma/range page list, e.g. 1,4,16-27.")
    parser.add_argument("--gpu", action="store_true", help="Ask PaddleOCR to use GPU when supported.")
    parser.add_argument(
        "--engine",
        choices=["auto", "paddle", "rapidocr"],
        default="rapidocr",
        help="OCR engine. auto tries PaddleOCR then RapidOCR fallback.",
    )
    args = parser.parse_args()

    ocr_pages(parse_pages(args.pages), use_gpu=args.gpu, engine=args.engine)


if __name__ == "__main__":
    main()
