from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import onnx
import onnx.helper as oh
import onnxruntime as ort
from onnx import TensorProto

from gpu_runtime import configure_gpu_runtime, preload_onnxruntime_cuda


def build_add_model(path: Path) -> None:
    x = oh.make_tensor_value_info("x", TensorProto.FLOAT, [2, 2])
    y = oh.make_tensor_value_info("y", TensorProto.FLOAT, [2, 2])
    z = oh.make_tensor_value_info("z", TensorProto.FLOAT, [2, 2])
    node = oh.make_node("Add", ["x", "y"], ["z"])
    graph = oh.make_graph([node], "gpu_smoke_add", [x, y], [z])
    model = oh.make_model(
        graph,
        opset_imports=[oh.make_operatorsetid("", 17)],
        ir_version=8,
    )
    onnx.checker.check_model(model)
    onnx.save(model, path)


def main() -> None:
    dll_dirs = configure_gpu_runtime()
    ok, preload_message = preload_onnxruntime_cuda()
    print("DLL directories:")
    for path in dll_dirs:
        print(f"  {path}")
    print(preload_message)
    print("ONNXRuntime:", ort.__version__)
    print("Available providers:", ort.get_available_providers())

    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / "add.onnx"
        build_add_model(model_path)
        session = ort.InferenceSession(
            str(model_path),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        providers = session.get_providers()
        print("Session providers:", providers)
        a = np.ones((2, 2), dtype=np.float32)
        b = np.full((2, 2), 2, dtype=np.float32)
        result = session.run(None, {"x": a, "y": b})[0]
        print("Result:", result.tolist())
        if providers[0] != "CUDAExecutionProvider":
            raise SystemExit("CUDAExecutionProvider was not selected as the primary provider.")
        if not np.allclose(result, 3):
            raise SystemExit("Unexpected ONNXRuntime result.")
    if not ok:
        raise SystemExit(preload_message)
    try:
        from rapidocr import RapidOCR

        engine = RapidOCR(
            params={
                "Global.log_level": "warning",
                "EngineConfig.onnxruntime.use_cuda": True,
            }
        )
        rapid_sessions = {
            "det": engine.text_det.session.session.get_providers(),
            "cls": engine.text_cls.session.session.get_providers(),
            "rec": engine.text_rec.session.session.get_providers(),
        }
        print("RapidOCR providers:", rapid_sessions)
        for name, providers in rapid_sessions.items():
            if providers[0] != "CUDAExecutionProvider":
                raise SystemExit(f"RapidOCR {name} session is not using CUDA first: {providers}")
    except ImportError:
        print("RapidOCR is not installed; skipped RapidOCR provider check.")
    print("GPU runtime smoke test passed.")


if __name__ == "__main__":
    main()
