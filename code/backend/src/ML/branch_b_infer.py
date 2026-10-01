import io
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional


# --------------------
# Constants
# --------------------
SR = 16000
TRAIN_WIN_SEC = 12  # training window length used when ONNX was exported
INFER_WINS = 3
INFER_OVERLAP = 0.5
WIN = SR * TRAIN_WIN_SEC

# Model paths
MODEL_DIR = Path(__file__).parent / "model"
ONNX_INT8_PATH = MODEL_DIR / "branch_b_int8.onnx"
ONNX_PATH = MODEL_DIR / "branch_b.onnx"


# -----------------------------
# Audio Loading
# -----------------------------
def read_audio_16k(path: Path):
    """Returns mono 16kHz float32 numpy array. Uses CPU-only resampling."""
    x, sr = sf.read(str(path), always_2d=False)

    # Convert to mono if stereo
    if isinstance(x, np.ndarray) and x.ndim > 1:
        x = x.mean(axis=1)

    x = x.astype(np.float32)

    if sr != SR:
        # simple linear resample
        duration = len(x) / sr
        new_len = int(duration * SR)
        x = np.interp(
            np.linspace(0, len(x), new_len, endpoint=False),
            np.arange(len(x)),
            x
        ).astype(np.float32)

    return x, SR


def read_audio_16k_from_bytes(audio_bytes: bytes):
    """Returns mono 16kHz float32 numpy array from in-memory bytes."""
    # Use soundfile to read from BytesIO
    audio_buffer = io.BytesIO(audio_bytes)
    x, sr = sf.read(audio_buffer, always_2d=False)

    # Convert to mono if stereo
    if isinstance(x, np.ndarray) and x.ndim > 1:
        x = x.mean(axis=1)

    x = x.astype(np.float32)

    if sr != SR:
        # simple linear resample
        duration = len(x) / sr
        new_len = int(duration * SR)
        x = np.interp(
            np.linspace(0, len(x), new_len, endpoint=False),
            np.arange(len(x)),
            x
        ).astype(np.float32)

    return x, SR

# ----------------------
# Sliding window helper
# ----------------------
def sliding_windows_indices(n, win, overlap, max_wins):
    if n <= win: 
        return [(0, n)]
    hop = max(1, int(win * (1 - overlap)))
    starts = list(range(0, max(n - win, 0) + 1, hop))
    if starts[-1] != n - win: 
        starts.append(n - win)
    return [(s, s+win) for s in starts[:max_wins]]



# -----------------------------
# ONNX Runtime Inference (Memory Efficient)
# -----------------------------
class ONNXBranchBModel:
    """ONNX Runtime-based inference with a small memory footprint."""
    
    def __init__(self, onnx_path: Path):
        import onnxruntime as ort
        
        # Configure session options for minimal memory
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 2
        sess_options.inter_op_num_threads = 1
        # Enable memory pattern optimization
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True
        
        self.session = ort.InferenceSession(
            str(onnx_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        
    def __call__(self, audio_np: np.ndarray) -> np.ndarray:
        """Run inference on audio array. Shape: (batch, samples) or (samples,)"""
        if audio_np.ndim == 1:
            audio_np = audio_np[np.newaxis, :]
        
        audio_np = audio_np.astype(np.float32)
        outputs = self.session.run(
            [self.output_name], 
            {self.input_name: audio_np}
        )
        return outputs[0]


# -----------------------------
# Load model (ONNX only)
# -----------------------------
def load_branch_b_model(onnx_path: Optional[Path] = None) -> ONNXBranchBModel:
    """
    Load Branch B model for inference (ONNX only).

    If a specific path is provided it must exist. Otherwise the loader
    prefers the quantized int8 model and falls back to the float32 model.
    """
    if onnx_path is not None:
        onnx_path = Path(onnx_path)
        if not onnx_path.exists():
            raise FileNotFoundError(f"Branch B ONNX file not found at {onnx_path}")
        print(f"Loading ONNX model: {onnx_path}")
        return ONNXBranchBModel(onnx_path)

    candidates = [p for p in (ONNX_INT8_PATH, ONNX_PATH) if p.exists()]
    if not candidates:
        raise FileNotFoundError(
            f"No ONNX model available. Expected one of: {ONNX_INT8_PATH} or {ONNX_PATH}"
        )

    selected = candidates[0]
    print(f"Loading ONNX model: {selected}")
    return ONNXBranchBModel(selected)

# ----------------------
# Scoring on numpy audio
# ----------------------
def _sigmoid(x):
    """Numpy sigmoid function."""
    return 1 / (1 + np.exp(-x))


def score_np_audio(model, x_np: np.ndarray):
    """Score audio using the ONNX Branch B model."""
    x_np = x_np.astype(np.float32, copy=False)
    
    idxs = sliding_windows_indices(
        len(x_np), WIN, INFER_OVERLAP, INFER_WINS
    )

    windows = []
    for s, e in idxs:
        w = x_np[s:e]
        if len(w) < WIN:
            tmp = np.zeros(WIN, dtype=np.float32)
            tmp[:len(w)] = w
            w = tmp
        windows.append(w)

    if not windows:
        windows = [np.zeros(WIN, dtype=np.float32)]

    if not isinstance(model, ONNXBranchBModel):
        raise TypeError("Branch B now supports ONNX models only.")

    # ONNX inference - process windows one at a time (model expects batch=1)
    all_logits = []
    for w in windows:
        logit = model(w[np.newaxis, :])  # Add batch dimension
        all_logits.append(logit[0])
    probs = _sigmoid(np.array(all_logits))

    return float(np.median(probs)), probs


# -----------------------------
# Sliding window scoring
# -----------------------------
# def sliding_windows(n, win, overlap, max_wins):
#     if n <= win:
#         return [(0, n)]
#     hop = max(1, int(win * (1 - overlap)))
#     starts = list(range(0, n - win + 1, hop))
#     if starts[-1] != n - win:
#         starts.append(n - win)
#     return [(s, s+win) for s in starts[:max_wins]]

# ----------------------
# Public API for FastAPI Backend
# ----------------------
def run_branch_b(model, audio_path: Path):
    """Main entrypoint: Load audio → sliding window → model → probability."""
    x, sr = read_audio_16k(audio_path)
    if sr != SR:
        raise RuntimeError(f"Expected {SR} Hz audio, got {sr}")
    
    prob, win_probs = score_np_audio(model, x)
    
    return {
        "prob": float(prob),
        "wins": [float(p) for p in win_probs.tolist()],
        "duration_sec": len(x) / SR,
    }


def run_branch_b_from_bytes(model, audio_bytes: bytes):
    """Main entrypoint for in-memory audio: bytes → sliding window → model → probability."""
    x, sr = read_audio_16k_from_bytes(audio_bytes)
    if sr != SR:
        raise RuntimeError(f"Expected {SR} Hz audio, got {sr}")
    
    prob, win_probs = score_np_audio(model, x)
    
    return {
        "prob": float(prob),
        "wins": [float(p) for p in win_probs.tolist()],
        "duration_sec": len(x) / SR,
    }
    # return {
    #     "prob": prob,
    #     "pred": int(prob >= 0.5),
    #     "win_scores": all_probs,
    #     "duration_sec": len(x) / SR,
    #     "sr": SR
    # }
