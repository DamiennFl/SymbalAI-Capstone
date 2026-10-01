from pathlib import Path
from itertools import chain
import argparse, json, time
from typing import List, Tuple
import numpy as np
from faster_whisper import WhisperModel
from ML.read_score_branch_a import score_file

EXTS = ("*.wav", "*.flac", "*.mp3")

def collect_files(pos_dir: Path, neg_dir: Path, exts=EXTS) -> Tuple[List[Path], List[Path]]:
    def grab(root: Path):
        return list(chain.from_iterable(root.rglob(pat) for pat in exts))
    pos = sorted(grab(Path(pos_dir)))
    neg = sorted(grab(Path(neg_dir)))
    return pos, neg

def eval_dirs(pos_dir: Path, neg_dir: Path, model_size: str, compute_type: str, device: str, progress_every: int = 10):
    model = WhisperModel(model_size, compute_type=compute_type, device=device)
    pos_files, neg_files = collect_files(pos_dir, neg_dir)
    total = len(pos_files) + len(neg_files)
    if total == 0:
        raise SystemExit(f"No audio found. Checked {pos_dir} and {neg_dir} with extensions {EXTS}.")

    y_true, y_pred = [], []
    start = time.time()

    def run_files(files, label, offset):
        for idx, p in enumerate(files, 1):
            res = score_file(model, str(p))
            y_true.append(label)
            y_pred.append(res["reading_likelihood"])
            processed = offset + idx
            if processed % progress_every == 0 or processed == total:
                elapsed = time.time() - start
                rate = processed / max(1e-9, elapsed)
                eta = (total - processed) / max(1e-9, rate)
                print(f"Processed {processed}/{total} | elapsed {elapsed:.1f}s | {rate:.2f} f/s | ETA {eta:.1f}s")

    run_files(pos_files, 0, 0)
    run_files(neg_files, 1, len(pos_files))

    y_pred_arr = np.array(y_pred)
    y_true_arr = np.array(y_true)
    preds_01 = (y_pred_arr >= 0.5).astype(int)

    acc = float((preds_01 == y_true_arr).mean())
    tp = int(((preds_01 == 1) & (y_true_arr == 1)).sum())
    tn = int(((preds_01 == 0) & (y_true_arr == 0)).sum())
    fp = int(((preds_01 == 1) & (y_true_arr == 0)).sum())
    fn = int(((preds_01 == 0) & (y_true_arr == 1)).sum())

    print(f"\nFiles: pos={len(pos_files)} neg={len(neg_files)} total={total}")
    print(f"Accuracy @0.5: {acc:.3f}")
    print("Confusion matrix (rows=true, cols=pred):")
    print(f"    [[TN={tn}  FP={fp}]\n     [FN={fn}  TP={tp}]]")

    return {
        "files": {"pos": len(pos_files), "neg": len(neg_files)},
        "accuracy": acc,
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "probs": y_pred,
        "labels": y_true,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pos_dir", required=True)
    ap.add_argument("--neg_dir", required=True)
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--compute_type", default="float16")
    ap.add_argument("--device", default="cuda", help="faster-whisper device: cuda/cpu")
    ap.add_argument("--progress_every", type=int, default=10, help="Print progress every N files")
    ap.add_argument("--json_out", help="Optional path to save detailed results")
    args = ap.parse_args()

    out = eval_dirs(
        Path(args.pos_dir),
        Path(args.neg_dir),
        args.model,
        args.compute_type,
        args.device,
        args.progress_every,
    )
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
