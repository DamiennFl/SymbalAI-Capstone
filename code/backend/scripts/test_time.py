import time
from src.services.branch_a_reader import analyze_audio_branch_a, MODEL
from src.ML.branch_b_infer import load_branch_b_model, run_branch_b
from pathlib import Path

import sys, pathlib
repo_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.append(str(repo_root / "code" / "backend"))

audio_path = Path("PATH TO .WAV, .FLAC, OR .MP3 FILE")

t0 = time.perf_counter()
_ = analyze_audio_branch_a(audio_path.open("rb"))
t1 = time.perf_counter()
b_model = load_branch_b_model()
_ = run_branch_b(b_model, audio_path)
t2 = time.perf_counter()

print(f"Branch A: {(t1-t0)*1000:.0f} ms")
print(f"Branch B: {(t2-t1)*1000:.0f} ms")