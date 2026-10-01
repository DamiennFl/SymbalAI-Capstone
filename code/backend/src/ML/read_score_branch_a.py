#!/usr/bin/env python3
# Imports
import argparse, re, math, json, os, sys, io
from typing import List, Dict, Any, Tuple, Union
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
import syllables
from rich.console import Console
from rich.table import Table

# Target sample rate for Whisper
WHISPER_SR = 16000

# Initialize console
console = Console()

# Filler words (normalized tokens)
UNIGRAM_FILLERS = {
    "uh","um","erm","er","uhh","umm","mm","hmm","uhm",
    "like","ya","kinda","sorta","basically","actually","literally",
}
MULTIWORD_FILLERS = [
    ("you","know"),
    ("i","mean"),
    ("sort","of"),
    ("kind","of"),
    ("you","know","what"),
]

# Learned logistic regression params for Branch A (1 = reading/negative)
LOGREG_PARAMS = {
    "intercept": -1.7518816748312314,
    "coef": {
        "interword_cv": -3.0130200640817963,
        "pauses_per_min": -0.950567764456191,
        "silence_ratio": 2.422769821756701,
        "phrase_len_cv": -0.44816489650220964,
        "disfluencies_per_100w": -4.419447449434091,
        "repetitions_per_100w": -0.8156718677757627,
    },
    "mean": {
        "interword_cv": 0.8572724831929792,
        "pauses_per_min": 8.78702403705708,
        "silence_ratio": 0.1228530230559699,
        "phrase_len_cv": 0.5691341705284514,
        "disfluencies_per_100w": 1.8917724784990562,
        "repetitions_per_100w": 0.25221018577777954,
    },
    "scale": {
        "interword_cv": 0.28485168909981806,
        "pauses_per_min": 5.586927818969286,
        "silence_ratio": 0.09352070015242622,
        "phrase_len_cv": 0.16998325392277439,
        "disfluencies_per_100w": 3.0179673327535776,
        "repetitions_per_100w": 0.7315129266515135,
    },
}

LOGREG_FEATURES = [
    "interword_cv",
    "pauses_per_min",
    "silence_ratio",
    "phrase_len_cv",
    "disfluencies_per_100w",
    "repetitions_per_100w",
]

# Normalize tokens
def normalize_token(t: str) -> str:
    """Lowercase and remove non-alpha characters."""
    t = t.lower()
    return re.sub(r"[^a-z]", "", t)

# Sigmoid function
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

# Transcribe words with timestamps
def transcribe_words(model: WhisperModel, path: str):
    # Use VAD filtering to skip silences.
    # Use faster_whisper model to transcribe.
    segments, _ = model.transcribe(
        path,
        word_timestamps=True,
        vad_filter=False,
        vad_parameters=dict(min_silence_duration_ms=200),
        language="en"
    )
    # Collect words with timestamps
    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                if not w.word: 
                    continue
                txt = w.word.strip()
                if not txt:
                    continue
                words.append({"text": txt, "start": float(w.start), "end": float(w.end)})
    clean_words = [w for w in words if w["start"] is not None and w["end"] is not None]
    audio_start = 0.0
    audio_end = 0.0
    if segments:
        try:
            audio_start = float(getattr(segments[0], "start", 0.0) or 0.0)
            audio_end = float(getattr(segments[-1], "end", 0.0) or 0.0)
        except Exception:
            audio_start, audio_end = 0.0, 0.0
    elif clean_words:
        audio_end = float(clean_words[-1]["end"])
    return clean_words, (audio_start, audio_end)


def transcribe_words_from_array(model: WhisperModel, audio_array: np.ndarray):
    """Transcribe from a numpy array (16kHz float32 mono).
    faster-whisper accepts numpy arrays directly."""
    segments, _ = model.transcribe(
        audio_array,
        word_timestamps=True,
        vad_filter=False,
        vad_parameters=dict(min_silence_duration_ms=200),
        language="en"
    )
    # Collect words with timestamps
    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                if not w.word: 
                    continue
                txt = w.word.strip()
                if not txt:
                    continue
                words.append({"text": txt, "start": float(w.start), "end": float(w.end)})
    clean_words = [w for w in words if w["start"] is not None and w["end"] is not None]
    audio_start = 0.0
    audio_end = 0.0
    if segments:
        try:
            audio_start = float(getattr(segments[0], "start", 0.0) or 0.0)
            audio_end = float(getattr(segments[-1], "end", 0.0) or 0.0)
        except Exception:
            audio_start, audio_end = 0.0, 0.0
    elif clean_words:
        audio_end = float(clean_words[-1]["end"])
    return clean_words, (audio_start, audio_end)


def compute_features(
    words: List[Dict[str, Any]],
    audio_bounds: Tuple[float, float] | None = None,
) -> Dict[str, Any]:
    """Compute timing and disfluency features from word timestamps."""
    if not words:
        total_duration = 0.0
        if audio_bounds is not None:
            total_duration = max(0.0, float(audio_bounds[1]) - float(audio_bounds[0]))
        return {
            "duration_s": total_duration,
            "word_count": 0,
            "syllables": 0,
            "speaking_time_s": 0.0,
            "silence_time_s": total_duration,
            "silence_ratio": 0.0,
            "pauses_per_min": 0.0,
            "long_pause_rate_pm": 0.0,
            "interword_cv": None,
            "phrase_len_cv": None,
            "disfluencies_per_100w": 0.0,
            "repetitions_per_100w": 0.0,
            "articulation_rate_syl_per_s": 0.0,
            "leading_silence_s": total_duration,
            "trailing_silence_s": 0.0,
        }

    starts = [w["start"] for w in words]
    ends = [w["end"] for w in words]
    first_start = starts[0]
    last_end = ends[-1]

    audio_start, audio_end = (0.0, last_end)
    if audio_bounds is not None:
        audio_start = float(audio_bounds[0])
        audio_end = float(audio_bounds[1])
    audio_start = min(audio_start, first_start)
    audio_end = max(audio_end, last_end)
    total_duration = max(0.0, audio_end - audio_start)

    gaps, onsets = [], []
    for i in range(len(words) - 1):
        gap = max(0.0, words[i + 1]["start"] - words[i]["end"])
        gaps.append(gap)
        onsets.append(max(1e-6, words[i + 1]["start"] - words[i]["start"]))

    PAUSE_TH = 0.35
    LONG_PAUSE_TH = 0.80

    pauses = [g for g in gaps if g >= PAUSE_TH]
    long_pauses = [g for g in gaps if g >= LONG_PAUSE_TH]

    leading_sil = max(0.0, first_start - audio_start)
    trailing_sil = max(0.0, audio_end - last_end)
    silence_time = float(sum(pauses) + leading_sil + trailing_sil)
    speaking_time = max(0.0, total_duration - silence_time)

    toks = [normalize_token(w["text"]) for w in words if w["text"].strip()]
    toks = [t for t in toks if t]
    word_count = len(toks)
    syl_count = sum(syllables.estimate(re.sub(r"[^a-zA-Z]", "", w["text"])) for w in words)

    disfluencies = sum(1 for t in toks if t in UNIGRAM_FILLERS)

    def count_multiword(tokens: List[str], patterns: List[tuple[str, ...]]) -> int:
        total = 0
        n = len(tokens)
        for pat in patterns:
            m = len(pat)
            if m == 0 or m > n:
                continue
            for i in range(0, n - m + 1):
                if tokens[i:i + m] == list(pat):
                    total += 1
        return total

    disfluencies += count_multiword(toks, MULTIWORD_FILLERS)
    disfl_100w = (disfluencies / max(1, word_count)) * 100.0

    reps = sum(
        1
        for i in range(1, len(toks))
        if toks[i]
        and toks[i] == toks[i - 1]
        and toks[i] not in {"the", "and"}
    )
    reps_100w = (reps / max(1, word_count)) * 100.0

    interword_cv = None
    if len(onsets) >= 5:
        mean_onset = float(np.mean(onsets))
        std_onset = float(np.std(onsets))
        if mean_onset > 1e-6:
            interword_cv = std_onset / mean_onset

    phrase_lengths = []
    cur = 1
    for g in gaps:
        if g >= LONG_PAUSE_TH:
            if cur > 0:
                phrase_lengths.append(cur)
            cur = 1
        else:
            cur += 1
    if cur > 0:
        phrase_lengths.append(cur)
    phrase_len_cv = None
    if len(phrase_lengths) >= 3:
        m = float(np.mean(phrase_lengths))
        s = float(np.std(phrase_lengths))
        if m > 1e-6:
            phrase_len_cv = s / m

    pauses_per_min = (len(pauses) / max(1e-6, total_duration)) * 60.0
    long_pause_rate_pm = (len(long_pauses) / max(1e-6, total_duration)) * 60.0
    silence_ratio = silence_time / max(1e-6, total_duration)
    artic_rate = (syl_count / max(1e-6, speaking_time)) if speaking_time > 0 else 0.0

    return {
        "duration_s": float(total_duration),
        "word_count": int(word_count),
        "syllables": int(syl_count),
        "speaking_time_s": float(speaking_time),
        "silence_time_s": float(silence_time),
        "silence_ratio": float(silence_ratio),
        "pauses_per_min": float(pauses_per_min),
        "long_pause_rate_pm": float(long_pause_rate_pm),
        "interword_cv": interword_cv,
        "phrase_len_cv": phrase_len_cv,
        "disfluencies_per_100w": float(disfl_100w),
        "repetitions_per_100w": float(reps_100w),
        "articulation_rate_syl_per_s": float(artic_rate),
        "leading_silence_s": float(leading_sil),
        "trailing_silence_s": float(trailing_sil),
    }


def logistic_reading_score(feat: Dict[str, Any]) -> Dict[str, Any]:
    """Standardized logistic regression probability that the clip is reading."""
    short = feat["duration_s"] < 10 or feat["word_count"] < 30
    note = "short_audio_low_confidence" if short else "ok"

    z = LOGREG_PARAMS["intercept"]
    for name in LOGREG_FEATURES:
        x = feat.get(name, None)
        m = LOGREG_PARAMS["mean"][name]
        s = LOGREG_PARAMS["scale"][name]
        if x is None:
            x = m
        z += LOGREG_PARAMS["coef"][name] * ((x - m) / s)
    prob = sigmoid(z)

    return {
        "score": float(prob),
        "parts": {"logit": float(z)},
        "note": note,
    }

def score_file(model: WhisperModel, path: str) -> Dict[str, Any]:
    words, audio_bounds = transcribe_words(model, path)
    feat = compute_features(words, audio_bounds)
    s = logistic_reading_score(feat)
    return {
        "file": path,
        "features": feat,
        "reading_likelihood": s["score"],
        "subscores": s.get("parts", {}),
        "note": s.get("note", "ok"),
    }


def transcribe_words_from_buffer(model: WhisperModel, audio_buffer: Union[io.BytesIO, io.BufferedReader]):
    """Transcribe from an in-memory buffer using numpy array.
    faster-whisper accepts numpy arrays directly, so no temp file is needed."""
    # Reset buffer position
    audio_buffer.seek(0)
    
    # Load audio from buffer using soundfile
    audio_data, sr = sf.read(audio_buffer, dtype='float32')
    
    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)
    
    # Resample to 16kHz if needed (Whisper requirement)
    if sr != WHISPER_SR:
        duration = len(audio_data) / sr
        new_len = int(duration * WHISPER_SR)
        audio_data = np.interp(
            np.linspace(0, len(audio_data), new_len, endpoint=False),
            np.arange(len(audio_data)),
            audio_data
        ).astype(np.float32)
    
    # Pass numpy array directly to faster_whisper
    return transcribe_words_from_array(model, audio_data)


def score_file_from_buffer(model: WhisperModel, audio_buffer: Union[io.BytesIO, io.BufferedReader]) -> Dict[str, Any]:
    """Score audio from an in-memory buffer."""
    words, audio_bounds = transcribe_words_from_buffer(model, audio_buffer)
    feat = compute_features(words, audio_bounds)
    s = logistic_reading_score(feat)
    return {
        "file": "<memory>",
        "features": feat,
        "reading_likelihood": s["score"],
        "subscores": s.get("parts", {}),
        "note": s.get("note", "ok"),
    }


def main():
    ap = argparse.ArgumentParser(description="Branch-A reading likelihood scorer (text+timing).")
    ap.add_argument("files", nargs="+", help="Audio files to score")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--compute_type", default="auto")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    results = []
    for f in args.files:
        if not os.path.isfile(f):
            console.print(f"[red]Missing file:[/red] {f}")
            sys.exit(1)
        results.append(score_file(model, f))

    if args.json:
        print(json.dumps(results, indent=2))
        return

    table = Table(title="Reading (cheating) likelihood - Branch A")
    table.add_column("File"); table.add_column("Score [0..1]")
    table.add_column("Words"); table.add_column("Dur(s)")
    table.add_column("Silence"); table.add_column("Pauses/min")
    table.add_column("Interword CV"); table.add_column("PhraseLen CV")
    for r in results:
        f = r["features"]
        table.add_row(
            os.path.basename(r["file"]),
            f"{r['reading_likelihood']:.2f}",
            str(f["word_count"]),
            f"{f['duration_s']:.1f}",
            f"{f['silence_ratio']:.2f}",
            f"{f['pauses_per_min']:.1f}",
            f"{f['interword_cv']:.2f}" if f["interword_cv"] is not None else "?",
            f"{f['phrase_len_cv']:.2f}" if f["phrase_len_cv"] is not None else "?",
        )
    console.print(table)
    console.print("\nJSON output:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
