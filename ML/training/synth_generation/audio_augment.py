#!/usr/bin/env python3
import argparse, json, math, os, sys, random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
import numpy as np
import soundfile as sf
from scipy import signal
import librosa

def load_audio(path: str, target_sr: int=48000) -> Tuple[np.ndarray, int]:
    y, sr = librosa.load(path, sr=None, mono=True)
    if sr != target_sr:
        y = librosa.resample(y, orig_sr=sr, target_sr=target_sr, res_type='kaiser_best')
        sr = target_sr
    y = np.asarray(y, dtype=np.float32)
    y = np.clip(y, -1.0, 1.0)
    return (y, sr)

def save_wav(path: str, y: np.ndarray, sr: int):
    y = np.asarray(y, dtype=np.float32)
    y = np.clip(y, -1.0, 1.0)
    sf.write(path, y, sr, subtype='PCM_16')

def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.maximum(1e-12, x ** 2))))

def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)

def lin_to_db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-12))

def softclip(x: np.ndarray, drive: float=1.0) -> np.ndarray:
    return np.tanh(drive * x)

def mu_law_encode(x: np.ndarray, mu: int=255) -> np.ndarray:
    x = np.clip(x, -1.0, 1.0)
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = np.round((y + 1) * 127.5).astype(np.int16)
    return q

def mu_law_decode(q: np.ndarray, mu: int=255) -> np.ndarray:
    y = q.astype(np.float32) / 127.5 - 1.0
    x = np.sign(y) * (np.expm1(np.abs(y) * np.log1p(mu)) / mu)
    return np.clip(x, -1.0, 1.0).astype(np.float32)

def apply_iir(y: np.ndarray, b, a) -> np.ndarray:
    zi = signal.lfilter_zi(b, a) * y[0]
    out, _ = signal.lfilter(b, a, y, zi=zi)
    return out.astype(np.float32)

def butter_bandpass(low, high, sr, order=4):
    return signal.butter(order, [low / (sr / 2), high / (sr / 2)], btype='band')

def butter_lowpass(cut, sr, order=6):
    return signal.butter(order, cut / (sr / 2), btype='low')

def pink_noise_like(n: int, rng: random.Random) -> np.ndarray:
    wn = np.random.RandomState(rng.randrange(1 << 31)).normal(0, 1, n).astype(np.float32)
    b, a = signal.butter(1, 0.1, btype='low')
    pn = apply_iir(wn, b, a)
    pn /= max(rms(pn), 1e-06)
    return pn

def add_noise(y: np.ndarray, snr_db: float, color: str, rng: random.Random) -> np.ndarray:
    sig_r = rms(y)
    if sig_r < 1e-09:
        return y
    n = len(y)
    if color == 'white':
        noise = np.random.RandomState(rng.randrange(1 << 31)).normal(0, 1, n).astype(np.float32)
        noise /= max(rms(noise), 1e-06)
    else:
        noise = pink_noise_like(n, rng)
    noise_gain = sig_r / db_to_lin(snr_db)
    return np.clip(y + noise_gain * noise, -1.0, 1.0)

def add_hum(y: np.ndarray, sr: int, freq: float, gain_db: float, rng: random.Random) -> np.ndarray:
    t = np.arange(len(y)) / sr
    phase = 2 * np.pi * rng.random()
    hum = np.sin(2 * np.pi * freq * t + phase)
    hum += 0.3 * np.sin(2 * np.pi * 2 * freq * t + phase)
    hum += 0.15 * np.sin(2 * np.pi * 3 * freq * t + phase)
    hum = hum.astype(np.float32)
    hum /= max(rms(hum), 1e-06)
    return np.clip(y + db_to_lin(gain_db) * hum, -1.0, 1.0)

def convolve_rir(y: np.ndarray, rir: np.ndarray, wet: float) -> np.ndarray:
    wet_sig = signal.fftconvolve(y, rir, mode='full')[:len(y)]
    wet_sig = wet_sig.astype(np.float32)
    if rms(wet_sig) > 1e-09:
        wet_sig *= rms(y) / rms(wet_sig)
    out = (1 - wet) * y + wet * wet_sig
    return np.clip(out, -1.0, 1.0)

def synthetic_small_room_ir(sr: int, decay_s: float, rng: random.Random) -> np.ndarray:
    length = int(sr * decay_s)
    if length < sr // 50:
        length = sr // 50
    ir = np.zeros(length, dtype=np.float32)
    for _ in range(6):
        pos = rng.randrange(0, min(length, int(sr * 0.03)))
        amp = 0.6 + 0.4 * rng.random()
        ir[pos] += amp
    else:
        pass
    t = np.arange(length) / sr
    tail = np.exp(-3.0 * t / decay_s) * np.random.RandomState(rng.randrange(1 << 31)).normal(0, 1, length)
    tail = tail.astype(np.float32)
    tail /= max(np.max(np.abs(tail)), 1e-09)
    ir = ir + 0.4 * tail
    ir /= max(np.max(np.abs(ir)), 1e-09)
    return ir

def compressor(y: np.ndarray, sr: int, thresh_db: float, ratio: float, attack_ms: float, release_ms: float) -> np.ndarray:
    eps = 1e-12
    env = 0.0
    atk = math.exp(-1.0 / (0.001 * attack_ms * sr))
    rel = math.exp(-1.0 / (0.001 * release_ms * sr))
    out = np.zeros_like(y)
    for i, x in enumerate(y):
        lvl = abs(x) + eps
        lvl_db = lin_to_db(lvl)
        over = max(0.0, lvl_db - thresh_db)
        gain_red_db = over - over / ratio
        target = db_to_lin(-gain_red_db)
        env = atk * env + (1 - atk) * target if target < env else rel * env + (1 - rel) * target
        out[i] = x * env
    else:
        pass
    return out.astype(np.float32)

def time_stretch(y: np.ndarray, rate: float) -> np.ndarray:
    if rate == 1.0:
        return y
    y_out = librosa.effects.time_stretch(y, rate=rate)
    return np.clip(y_out.astype(np.float32), -1.0, 1.0)

def resample_roundtrip(y: np.ndarray, sr: int, tgt_sr: int) -> np.ndarray:
    y_lo = librosa.resample(y, orig_sr=sr, target_sr=tgt_sr, res_type='kaiser_best')
    y_up = librosa.resample(y_lo, orig_sr=tgt_sr, target_sr=sr, res_type='kaiser_best')
    return np.clip(y_up.astype(np.float32), -1.0, 1.0)

def random_dropouts(y: np.ndarray, sr: int, prob_per_s: float, rng: random.Random) -> np.ndarray:
    y = y.copy()
    n = len(y)
    total_s = n / sr
    expected = prob_per_s * total_s
    k = np.random.RandomState(rng.randrange(1 << 31)).poisson(lam=max(expected, 0.0))
    for _ in range(k):
        dur_ms = rng.uniform(5, 40)
        dur = int(sr * dur_ms / 1000.0)
        start = rng.randrange(0, max(1, n - dur))
        y[start:start + dur] *= 0.0
    else:
        pass
    return y
INTENSITY_PRESETS = {'low': {'apply_counts': (0.65, 0.28, 0.07, 0.0), 'snr_db': (20, 30), 'reverb_wet': (0.05, 0.15), 'reverb_decay_s': (0.2, 0.45), 'lowpass_cut': (4500, 8000), 'bandpass': True, 'time_stretch': (0.97, 1.03), 'comp_thresh': (-8, -4), 'comp_ratio': (1.5, 2.5), 'hum_db': (-40, -32), 'dropouts_ps': (0.1, 0.3), 'mu_law': False, 'roundtrip_sr': (16000, 22050)}, 'med': {'apply_counts': (0.55, 0.3, 0.12, 0.03), 'snr_db': (12, 22), 'reverb_wet': (0.12, 0.28), 'reverb_decay_s': (0.3, 0.6), 'lowpass_cut': (3200, 5200), 'bandpass': True, 'time_stretch': (0.94, 1.06), 'comp_thresh': (-12, -6), 'comp_ratio': (2.0, 3.5), 'hum_db': (-38, -28), 'dropouts_ps': (0.2, 0.6), 'mu_law': True, 'roundtrip_sr': (16000, 16000)}, 'high': {'apply_counts': (0.4, 0.35, 0.2, 0.05), 'snr_db': (6, 16), 'reverb_wet': (0.2, 0.45), 'reverb_decay_s': (0.4, 0.9), 'lowpass_cut': (2200, 4200), 'bandpass': True, 'time_stretch': (0.9, 1.1), 'comp_thresh': (-18, -10), 'comp_ratio': (3.0, 6.0), 'hum_db': (-36, -24), 'dropouts_ps': (0.3, 1.0), 'mu_law': True, 'roundtrip_sr': (12000, 16000)}}
EFFECT_CATALOG = ['noise', 'reverb', 'bandlimit', 'lowpass', 'roundtrip', 'time_stretch', 'compress', 'softclip', 'hum', 'dropouts', 'mulaw']
EFFECT_WEIGHTS = {'noise': 1.0, 'reverb': 0.9, 'bandlimit': 0.7, 'lowpass': 0.6, 'roundtrip': 0.7, 'time_stretch': 0.8, 'compress': 0.6, 'softclip': 0.25, 'hum': 0.25, 'dropouts': 0.25, 'mulaw': 0.35}

@dataclass
class AugmentConfig:
    intensity: str = 'auto'
    rir_dir: Optional[str] = None

@dataclass
class AugmentMeta:
    seed: int
    intensity: str
    applied: List[Dict[str, float]]
    length_sec: float
    sr: int
    input_path: str
    output_path: str

def choose_intensity(intensity: str, rng: random.Random) -> str:
    if intensity == 'auto':
        return rng.choices(['low', 'med', 'high'], weights=[0.55, 0.35, 0.1], k=1)[0]
    if intensity not in INTENSITY_PRESETS:
        raise ValueError('intensity must be one of: auto, low, med, high')
    return intensity

def sample_effects(count_probs: Tuple[float, float, float, float], rng: random.Random) -> int:
    return rng.choices([0, 1, 2, 3], weights=list(count_probs), k=1)[0]

def pick_effect_list(k: int, rng: random.Random) -> List[str]:
    if k <= 0:
        return []
    items = EFFECT_CATALOG.copy()
    weights = np.array([EFFECT_WEIGHTS[e] for e in items], dtype=float)
    weights = weights / weights.sum()
    idxs = rng.sample(range(len(items)), k=len(items))
    idxs.sort(key=lambda i: weights[i], reverse=True)
    chosen = items[:k]
    rng.shuffle(chosen)
    return chosen

def maybe_load_random_rir(sr: int, rir_dir: Optional[str], rng: random.Random) -> Optional[np.ndarray]:
    if not rir_dir:
        return None
    p = Path(rir_dir)
    if not p.exists() or not p.is_dir():
        return None
    cands = [f for f in p.glob('**/*') if f.suffix.lower() in ('.wav', '.flac', '.ogg')]
    if not cands:
        return None
    sel = rng.choice(cands)
    rir, r_sr = librosa.load(str(sel), sr=None, mono=True)
    if r_sr != sr:
        rir = librosa.resample(rir, orig_sr=r_sr, target_sr=sr, res_type='kaiser_best')
    rir = rir.astype(np.float32)
    if np.max(np.abs(rir)) > 0:
        rir = rir / np.max(np.abs(rir))
    return rir

def apply_augmentations(y: np.ndarray, sr: int, seed: int, cfg: AugmentConfig) -> Tuple[np.ndarray, List[Dict[str, float]], str]:
    rng = random.Random(seed)
    intensity = choose_intensity(cfg.intensity, rng)
    preset = INTENSITY_PRESETS[intensity]
    k = sample_effects(preset['apply_counts'], rng)
    effects = pick_effect_list(k, rng)
    meta_applied: List[Dict[str, float]] = []
    rir = maybe_load_random_rir(sr, cfg.rir_dir, rng)
    if rir is None:
        decay_s = rng.uniform(*preset['reverb_decay_s'])
        rir = synthetic_small_room_ir(sr, decay_s, rng)
        rir_src = f'synthetic_{decay_s:.2f}s'
    else:
        rir_src = 'file_rir'
    y_out = y.copy()
    for e in effects:
        if e == 'noise':
            color = 'pink' if rng.random() < 0.6 else 'white'
            snr = rng.uniform(*preset['snr_db'])
            y_out = add_noise(y_out, snr_db=snr, color=color, rng=rng)
            meta_applied.append({'effect': 'noise', 'color': 1 if color == 'pink' else 0, 'snr_db': round(snr, 2)})
        elif e == 'reverb':
            wet = rng.uniform(*preset['reverb_wet'])
            y_out = convolve_rir(y_out, rir, wet=wet)
            meta_applied.append({'effect': 'reverb', 'wet': round(wet, 3), 'rir': rir_src})
        elif e == 'bandlimit':
            b, a = butter_bandpass(300.0, 3400.0, sr, order=4)
            y_out = apply_iir(y_out, b, a)
            meta_applied.append({'effect': 'bandlimit', 'low': 300.0, 'high': 3400.0})
        elif e == 'lowpass':
            cut = rng.uniform(*preset['lowpass_cut'])
            b, a = butter_lowpass(cut, sr, order=6)
            y_out = apply_iir(y_out, b, a)
            meta_applied.append({'effect': 'lowpass', 'cut': round(cut, 1)})
        elif e == 'roundtrip':
            tgt_sr = int(rng.choice(preset['roundtrip_sr']))
            y_out = resample_roundtrip(y_out, sr, tgt_sr=tgt_sr)
            meta_applied.append({'effect': 'roundtrip', 'tgt_sr': tgt_sr})
        elif e == 'time_stretch':
            lo, hi = preset['time_stretch']
            rate = rng.uniform(lo, hi)
            y_out = time_stretch(y_out, rate)
            meta_applied.append({'effect': 'time_stretch', 'rate': round(rate, 3)})
        elif e == 'compress':
            th = rng.uniform(*preset['comp_thresh'])
            ratio = rng.uniform(*preset['comp_ratio'])
            atk = rng.uniform(5, 20)
            rel = rng.uniform(50, 150)
            y_out = compressor(y_out, sr, thresh_db=th, ratio=ratio, attack_ms=atk, release_ms=rel)
            meta_applied.append({'effect': 'compress', 'th_db': round(th, 1), 'ratio': round(ratio, 2), 'attack_ms': round(atk, 1), 'release_ms': round(rel, 1)})
        elif e == 'softclip':
            drive = rng.uniform(1.1, 1.8)
            y_out = softclip(y_out, drive=drive)
            meta_applied.append({'effect': 'softclip', 'drive': round(drive, 2)})
        elif e == 'hum':
            freq = 50.0 if rng.random() < 0.5 else 60.0
            gain_db = rng.uniform(*preset['hum_db'])
            y_out = add_hum(y_out, sr, freq=freq, gain_db=gain_db, rng=rng)
            meta_applied.append({'effect': 'hum', 'freq': freq, 'gain_db': round(gain_db, 1)})
        elif e == 'dropouts':
            pps = rng.uniform(*preset['dropouts_ps'])
            y_out = random_dropouts(y_out, sr, prob_per_s=pps, rng=rng)
            meta_applied.append({'effect': 'dropouts', 'prob_per_s': round(pps, 3)})
        elif e == 'mulaw' and INTENSITY_PRESETS[intensity]['mu_law']:
            q = mu_law_encode(y_out, mu=255)
            y_out = mu_law_decode(q, mu=255)
            meta_applied.append({'effect': 'mulaw', 'bits': 8})
    else:
        pass
    peak = float(np.max(np.abs(y_out))) if len(y_out) else 0.0
    if peak > 0.999:
        y_out = 0.999 * y_out / peak
    return (y_out, meta_applied, intensity)

def main():
    ap = argparse.ArgumentParser(description='Audio augmentation (deterministic, metadata saved).')
    ap.add_argument('input', help='Input audio (mp3/wav)')
    ap.add_argument('--out', required=True, help='Output WAV path')
    ap.add_argument('--seed', type=int, required=True, help='Deterministic seed (store this!)')
    ap.add_argument('--intensity', default='auto', choices=['auto', 'low', 'med', 'high'], help='Augmentation strength')
    ap.add_argument('--rir-dir', default=None, help='Optional directory of RIR files (*.wav/*.flac/*.ogg)')
    args = ap.parse_args()
    inp = Path(args.input).expanduser().resolve()
    outp = Path(args.out).expanduser().resolve()
    outp.parent.mkdir(parents=True, exist_ok=True)
    y, sr = load_audio(str(inp), target_sr=48000)
    cfg = AugmentConfig(intensity=args.intensity, rir_dir=args.rir_dir)
    y_aug, applied, final_intensity = apply_augmentations(y, sr, seed=args.seed, cfg=cfg)
    save_wav(str(outp), y_aug, sr)
    meta = AugmentMeta(seed=args.seed, intensity=final_intensity, applied=applied, length_sec=round(len(y_aug) / sr, 3), sr=sr, input_path=str(inp), output_path=str(outp))
    meta_path = outp.with_suffix(outp.suffix + '.json')
    with open(meta_path, 'w') as f:
        json.dump(asdict(meta), f, indent=2)
    print(f'Saved: {outp}')
    print(f'Metadata: {meta_path}')
if __name__ == '__main__':
    main()
