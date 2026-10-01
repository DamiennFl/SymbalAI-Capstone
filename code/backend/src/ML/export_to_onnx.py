#!/usr/bin/env python3
"""
Utility script for Branch B ONNX artifacts.

This script now assumes an ONNX model already exists on disk. It can:
  - verify the float32 or int8 ONNX graphs run end-to-end
  - create an int8 quantized copy using ONNX Runtime (no PyTorch required)

Usage (from repo root):
    uv run python -m src.ML.export_to_onnx [--onnx-path PATH] [--no-quantize]
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import onnxruntime as ort

from src.ML.branch_b_infer import ONNX_INT8_PATH, ONNX_PATH, WIN


def verify_onnx(onnx_path: Path) -> bool:
    """Load and run a single forward pass to ensure the graph is usable."""
    session = ort.InferenceSession(
        str(onnx_path), providers=["CPUExecutionProvider"]
    )
    dummy_input = np.random.randn(1, WIN).astype(np.float32)
    outputs = session.run(None, {session.get_inputs()[0].name: dummy_input})
    if not outputs or outputs[0].size == 0:
        raise RuntimeError(f"ONNX graph at {onnx_path} returned no outputs")
    print(f"Verified ONNX model at {onnx_path} (output shape {outputs[0].shape})")
    return True


def quantize_to_int8(source: Path, target: Path) -> Path:
    """
    Create an int8 dynamic-quantized copy of the ONNX model.

    We restrict quantization to MatMul to avoid ConvInteger kernels that are
    not implemented by some CPU builds of onnxruntime (seen with WavLM convs).
    """
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic  # type: ignore
    except ImportError as e:
        raise ImportError(
            "Quantization requires the 'onnx' package. Install with "
            "`python -m pip install onnx` (or `python -m uv add onnx`) and retry."
        ) from e

    print(f"Quantizing {source} -> {target} ...")
    quantize_dynamic(
        model_input=str(source),
        model_output=str(target),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=["MatMul"],  # avoid ConvInteger for WavLM convs
    )
    print(
        f"Quantized model saved to {target} ({target.stat().st_size / 1024 / 1024:.1f} MB)"
    )
    return target


def main(onnx_path: Optional[Path], skip_quantize: bool) -> None:
    # Resolve source ONNX file
    source = Path(onnx_path) if onnx_path else ONNX_PATH
    if not source.exists():
        raise FileNotFoundError(
            f"Missing Branch B ONNX file. Expected {source} or provide --onnx-path"
        )

    print("=" * 60)
    print("Branch B ONNX verification")
    print("=" * 60)
    verify_onnx(source)

    # Optionally quantize
    if skip_quantize:
        print("Skipping int8 quantization (per flag).")
        return

    target = ONNX_INT8_PATH
    if target.exists():
        print(f"Int8 model already exists at {target}; verifying...")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        quantize_to_int8(source, target)
    verify_onnx(target)
    print("All ONNX artifacts verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify/quantize Branch B ONNX models")
    parser.add_argument("--onnx-path", type=Path, help="Path to existing float32 ONNX model")
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Skip creating/verifying the int8 variant",
    )
    args = parser.parse_args()
    main(args.onnx_path, args.no_quantize)
