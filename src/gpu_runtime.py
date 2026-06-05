from __future__ import annotations

import os
import site
from pathlib import Path


def candidate_cuda_dirs() -> list[Path]:
    dirs: list[Path] = []

    for site_path in site.getsitepackages():
        nvidia_root = Path(site_path) / "nvidia"
        if nvidia_root.exists():
            dirs.extend(path for path in nvidia_root.rglob("bin") if path.is_dir())

    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        dirs.append(Path(cuda_path) / "bin")

    default_cuda = Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA")
    if default_cuda.exists():
        dirs.extend(path / "bin" for path in default_cuda.iterdir() if path.is_dir())

    unique: list[Path] = []
    seen: set[str] = set()
    for path in dirs:
        resolved = str(path.resolve()).lower()
        if path.exists() and resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def configure_gpu_runtime() -> list[str]:
    added: list[str] = []
    for path in candidate_cuda_dirs():
        try:
            os.add_dll_directory(str(path))
            added.append(str(path))
        except (FileNotFoundError, OSError):
            continue
    return added


def preload_onnxruntime_cuda() -> tuple[bool, str]:
    configure_gpu_runtime()
    try:
        import onnxruntime as ort
    except ImportError as exc:
        return False, f"onnxruntime import failed: {exc}"

    preload = getattr(ort, "preload_dlls", None)
    if preload is None:
        return False, "onnxruntime.preload_dlls is unavailable"

    try:
        preload(directory="")
        return True, "onnxruntime CUDA/cuDNN DLL preload succeeded"
    except Exception as exc:
        return False, f"onnxruntime preload failed: {type(exc).__name__}: {exc}"

