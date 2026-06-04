#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

import fitz
from PIL import Image, ImageFilter, ImageOps


PDF_PATH = Path("sample.pdf")
PAGE_NUMBER = 22

# Coordinates are in page pixels after rendering with PyMuPDF scale=3.
# This crop contains the known target phrase: 成為溫暖的小幫手.
BASE_SCALE = 3.0
BASE_CHENGWEI_BOX = (800, 1790, 1180, 1920)


def scale_box(box: tuple[int, int, int, int], scale: float) -> tuple[int, int, int, int]:
    factor = scale / BASE_SCALE
    return tuple(round(value * factor) for value in box)


def render_page(pdf_path: Path, page_number: int, scale: float, output_path: Path) -> Path:
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(output_path)
    return output_path


def preprocess_crops(page_image: Path, output_dir: Path, scale: float) -> dict[str, str]:
    image = Image.open(page_image)
    box = scale_box(BASE_CHENGWEI_BOX, scale)
    crop = image.crop(box)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    raw = output_dir / "target_chengwei_raw.png"
    crop.save(raw)
    paths["raw"] = str(raw)

    enlarged = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
    enlarged_path = output_dir / "target_chengwei_enlarged.png"
    enlarged.save(enlarged_path)
    paths["enlarged"] = str(enlarged_path)

    gray = ImageOps.grayscale(enlarged)
    sharp = gray.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)
    sharp_path = output_dir / "target_chengwei_sharp.png"
    sharp.save(sharp_path)
    paths["sharp"] = str(sharp_path)

    binary = sharp.point(lambda pixel: 0 if pixel < 180 else 255, mode="1")
    binary_path = output_dir / "target_chengwei_binary.png"
    binary.save(binary_path)
    paths["binary"] = str(binary_path)

    return paths


def run_tesseract(image_path: str) -> dict:
    completed = subprocess.run(
        ["tesseract", image_path, "stdout", "-l", "chi_tra", "--psm", "7"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return {
        "method": "tesseract_chi_tra_psm7",
        "image_path": image_path,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_apple_vision(image_path: str) -> dict:
    script = Path("scripts/vision_ocr.swift")
    if not script.exists():
        return {
            "method": "apple_vision",
            "image_path": image_path,
            "error": "scripts/vision_ocr.swift not found",
        }
    completed = subprocess.run(
        ["swift", str(script), image_path],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return {
        "method": "apple_vision",
        "image_path": image_path,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Page 22 zhuyin OCR benchmark.")
    parser.add_argument("--pdf", type=Path, default=PDF_PATH)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/page22_benchmark"))
    parser.add_argument("--scales", nargs="+", type=float, default=[3.0, 4.0, 5.0])
    args = parser.parse_args()

    results = {
        "page": PAGE_NUMBER,
        "target_word": "成為",
        "expected_standard_zhuyin": "ㄔㄥˊ ㄨㄟˊ",
        "known_issue": "tone mismatch on 為",
        "runs": [],
    }

    for scale in args.scales:
        scale_dir = args.output_dir / f"scale_{scale:g}"
        page_image = scale_dir / "page22.png"
        render_page(args.pdf, PAGE_NUMBER, scale, page_image)
        crops = preprocess_crops(page_image, scale_dir, scale)

        run = {
            "scale": scale,
            "page_image": str(page_image),
            "crops": crops,
            "ocr_results": [],
        }
        for crop_path in crops.values():
            run["ocr_results"].append(run_tesseract(crop_path))
            run["ocr_results"].append(run_apple_vision(crop_path))
        results["runs"].append(run)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "results.json"
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
