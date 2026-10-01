import numpy as np
import soundfile as sf
import torch
from pathlib import Path
from transformers import WavLMModel


# --------------------
# Constants
# --------------------
SR = 16000
TRAIN_WIN_SEC = 12  # updated at load time from checkpoint
INFER_WINS = 3
INFER_OVERLAP = 0.5
WIN = SR * TRAIN_WIN_SEC

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# -----------------------------
# Audio Loading
# -----------------------------
# def read_audio_16k(path: Path):
#     """Returns mono 16k float32 numpy array."""
#     x, sr = sf.read(str(path), always_2d=False)
#     if isinstance(x, np.ndarray) and x.ndim > 1:
#         x = x.mean(axis=1)
#     x = x.astype(np.float32)

#     if sr != SR:
#         import torchaudio
#         t = torch.tensor(x).unsqueeze(0)
#         x = torchaudio.functional.resample(t, sr, SR)[0].numpy()

#     return x, SR
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
# WavLM model wrapper
# -----------------------------
class ReadVsSpont(torch.nn.Module):
    def __init__(self, enc_name="microsoft/wavlm-base-plus", head_dim=256):
        super().__init__()
        self.enc = WavLMModel.from_pretrained(enc_name)
        h = self.enc.config.hidden_size
        
        self.head = torch.nn.Sequential(
            torch.nn.Linear(h, head_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.30),
            torch.nn.Linear(head_dim, 1)
        )
        
        # encoder frozen
        for p in self.enc.parameters():
            p.requires_grad = False
        self.enc.eval()

    def forward(self, wav: torch.Tensor):
        out = self.enc(wav).last_hidden_state
        pooled = out.mean(dim=1)
        return self.head(pooled).squeeze(1)

# -----------------------------
# Load checkpoint
# -----------------------------
def load_branch_b_model(ckpt_path: Path, device="cpu"):
    ckpt = torch.load(ckpt_path, map_location=device)
    meta = ckpt.get("meta", {})
    
    enc_name = meta.get("ENC_NAME", "microsoft/wavlm-base-plus")

    model = ReadVsSpont(enc_name=enc_name).to(device)
    model.load_state_dict(ckpt["model"], strict=True)
    model.eval()
    return model

# ----------------------
# Scoring on numpy audio
# ----------------------
@torch.no_grad()
def score_np_audio(model, x_np: np.ndarray, device="cpu"):
    x_np = x_np.astype(np.float32, copy=False)
    
    idxs = sliding_windows_indices(
        len(x_np), WIN, INFER_OVERLAP, INFER_WINS
    )

    windows = []
    for s,e in idxs:
        w = x_np[s:e]
        if len(w) < WIN:
            tmp = np.zeros(WIN, dtype=np.float32)
            tmp[:len(w)] = w
            w = tmp
        windows.append(torch.from_numpy(w))

    if not windows:
        windows = [torch.from_numpy(np.zeros(WIN, dtype=np.float32))]

    W = torch.stack(windows).to(device)
    
    logits = model(W)
    probs = torch.sigmoid(logits).cpu().numpy()
    # with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
    #     logits = model(W)
    #     probs = torch.sigmoid(logits).cpu().numpy()

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
def run_branch_b(model, audio_path: Path, device="cpu"):
    """Main entrypoint: Load audio → sliding window → model → probability."""
    x, sr = read_audio_16k(audio_path)
    if sr != SR:
        raise RuntimeError(f"Expected {SR} Hz audio, got {sr}")
    
    prob, win_probs = score_np_audio(model, x, device=device)
    
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
