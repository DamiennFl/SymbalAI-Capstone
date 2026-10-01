import io

from .branch_a_reader import analyze_audio_branch_a
from src.ML.branch_b_infer import load_branch_b_model, run_branch_b_from_bytes

BRANCH_B_MODEL = load_branch_b_model()


def analyze_audio_bytes(audio_bytes: bytes):
    """Shared audio scoring logic (Branch A + Branch B) from in-memory bytes."""
    # ---- Branch A ----
    branch_a = analyze_audio_branch_a(io.BytesIO(audio_bytes))
    branch_a_score = float(branch_a["score"])

    # ---- Branch B ----
    branch_b = run_branch_b_from_bytes(BRANCH_B_MODEL, audio_bytes)
    branch_b_prob = float(branch_b["prob"])

    # ---- Combined Logic ----
    combined_risk = float((branch_b_prob * 0.6) + (branch_a_score * 0.4))

    if combined_risk >= 0.66:
        risk_label = "High"
    elif combined_risk >= 0.33:
        risk_label = "Medium"
    else:
        risk_label = "Low"

    return {
        "branch_a": {
            "score": branch_a_score,
            "metadata": branch_a["metadata"],
        },
        "branch_b": branch_b,
        "combined": {
            "score": combined_risk,
            "synthetic_prob": branch_b_prob,
            "reading_likelihood": branch_a_score,
            "risk_label": risk_label,
        },
    }


def analyze_audio(file):
    """HTTP-facing helper: read UploadFile and delegate to bytes-based scorer."""
    audio_bytes = file.file.read()
    return analyze_audio_bytes(audio_bytes)
