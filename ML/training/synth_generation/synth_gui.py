#!/usr/bin/env python3
import os
import sys
import json
import time
import uuid
import hashlib
import random
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import numpy as np
from synth_constants import sample_all_priors, POSITIVE_INSTRUCTIONS, NEGATIVE_INSTRUCTIONS
from audio_augment import load_audio, save_wav, apply_augmentations, AugmentConfig
try:
    import sounddevice as sd
    SOUNDDEV_OK = True
except Exception:
    SOUNDDEV_OK = False
else:
    pass
finally:
    pass
try:
    import simpleaudio as sa
    SIMPLEAUDIO_OK = True
except Exception:
    SIMPLEAUDIO_OK = False
else:
    pass
finally:
    pass
COLOR_CYAN = '#00bcd4'
COLOR_RED = '#a40000'
COLOR_ORANGE = '#a45f00'
COLOR_GREEN = '#2e7d32'
COLOR_TEXT = '#222222'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GEN_DIR = PROJECT_ROOT / 'synth_generation'
ANSWERS_PATH = GEN_DIR / 'answers' / 'answers_clean.txt'
OUTPUT_ROOT = GEN_DIR / 'output'
ENV_PATH = GEN_DIR / '.env'
VOICE_CACHE = GEN_DIR / 'voice_bank.json'
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
HUME_TTS_URL = 'https://api.hume.ai/v0/tts'
HUME_VOICES_URL = 'https://api.hume.ai/v0/tts/voices'
OVERSHOOT_MARGIN_SEC = 30

def load_env(path: Path) -> dict:
    res = {}
    if not path.exists():
        return res
    for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        res[k.strip()] = v.strip()
    else:
        pass
    return res

def save_env(path: Path, values: dict):
    cur = load_env(path)
    cur.update({k: v for k, v in values.items() if v is not None})
    lines = [f'{k}={cur[k]}' for k in sorted(cur.keys())]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def default_open_file(path: Path):
    p = str(path)
    if sys.platform.startswith('darwin'):
        os.spawnlp(os.P_NOWAIT, 'open', 'open', p)
    elif os.name == 'nt':
        os.startfile(p)
    else:
        os.spawnlp(os.P_NOWAIT, 'xdg-open', 'xdg-open', p)

def read_answers(path: Path) -> list[str]:
    if not path.exists():
        return ['Tell me about a challenging project and how you handled it.', 'What is your approach to prioritizing tasks with conflicting deadlines?', 'Describe a time you had to learn something quickly to deliver results.']
    lines = [ln.strip() for ln in path.read_text(encoding='utf-8', errors='ignore').splitlines()]
    return [x for x in lines if x]

def unique_stem(user: str, label: str) -> str:
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    uid = uuid.uuid4().hex[:8]
    safe_user = ''.join((c for c in user.strip() if c.isalnum() or c in ('-', '_'))) or 'user'
    return f'{ts}_{safe_user}_{label}_{uid}'

def seconds_to_mmss(sec: float) -> str:
    sec = max(0.0, float(sec))
    m = int(sec // 60)
    s = int(round(sec - 60 * m))
    return f'{m:02d}:{s:02d}'

def set_status(lbl: ttk.Label, text: str, color: str=COLOR_TEXT):
    lbl.config(text=text, foreground=color)

def qualitative_age(age: int) -> str:
    a = max(18, min(65, int(age)))
    if a <= 25:
        return 'early twenties'
    if a <= 28:
        return 'late twenties'
    if a <= 34:
        return 'early thirties'
    if a <= 37:
        return 'mid thirties'
    if a <= 45:
        return 'early forties'
    if a <= 55:
        return 'fifties'
    return 'early sixties'

def short_parameters_text(pri, label: str) -> str:
    g = pri.gender
    age_str = qualitative_age(pri.age)
    acc = pri.accent
    if acc and 'no marked accent' not in acc.lower():
        acc_txt = acc.replace('US ', '').replace('English', '').replace(' (no marked accent)', '').strip()
        accent_part = f'light {acc_txt} accent'
    else:
        accent_part = 'General American accent'
    style_tail = 'flat delivery.' if label == 'negative' else 'natural phrasing.'
    return f'{g} voice, {age_str} — {accent_part}; {style_tail}'

def identity_prompt_from_priors(pri) -> str:
    g = pri.gender
    age_str = qualitative_age(pri.age)
    acc = pri.accent
    if acc and 'no marked accent' not in acc.lower():
        acc_txt = acc.replace('US ', '').replace('English', '').replace(' (no marked accent)', '').strip()
        accent_part = f'light {acc_txt} accent'
    else:
        accent_part = 'General American accent'
    return f'{g} voice, {age_str}, {accent_part}; neutral timbre.'

def _voice_cache_get() -> dict:
    if VOICE_CACHE.exists():
        try:
            return json.loads(VOICE_CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {}
        else:
            pass
        finally:
            pass
    return {}

def _voice_cache_set(cache: dict):
    VOICE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_CACHE.write_text(json.dumps(cache, indent=2), encoding='utf-8')

def ensure_voice(api_key: str, identity_prompt: str) -> dict | None:
    cache = _voice_cache_get()
    key = hashlib.sha1(identity_prompt.encode('utf-8')).hexdigest()
    if key in cache:
        return cache[key]
    try:
        payload = {'version': '1', 'utterances': [{'text': 'This is a sample line for saving a reusable voice.', 'description': identity_prompt}], 'num_generations': 1, 'format': {'type': 'mp3'}, 'split_utterances': False}
        r = requests.post(HUME_TTS_URL, headers={'X-Hume-Api-Key': api_key}, json=payload, timeout=90)
        r.raise_for_status()
        gens = r.json().get('generations', [])
        if not gens or not gens[0].get('generation_id'):
            return None
        gen_id = gens[0]['generation_id']
    except Exception:
        return None
    else:
        pass
    finally:
        pass
    try:
        name = f'svy_{key[:10]}'
        r2 = requests.post(HUME_VOICES_URL, headers={'X-Hume-Api-Key': api_key}, json={'generation_id': gen_id, 'name': name}, timeout=60)
        r2.raise_for_status()
        v = r2.json()
        voice_ref = {'id': v.get('id'), 'name': v.get('name', name), 'provider': v.get('provider', 'CUSTOM_VOICE'), 'identity_prompt': identity_prompt, 'created_at': int(time.time())}
        cache[key] = voice_ref
        _voice_cache_set(cache)
        return voice_ref
    except Exception:
        return None
    else:
        pass
    finally:
        pass

def call_hume_tts(api_key: str, text: str, instruction: str, voice_ref: dict | None, speed_hint: float, trailing_silence: float):
    headers = {'Accept': 'application/json; charset=utf-8', 'X-Hume-Api-Key': api_key.strip()}
    utt = {'text': text, 'description': instruction, 'speed': float(speed_hint), 'trailing_silence': float(trailing_silence)}
    if voice_ref and voice_ref.get('id'):
        utt['voice'] = {'id': voice_ref['id']}
    payload = {'version': '1', 'utterances': [utt], 'format': {'type': 'mp3'}, 'num_generations': 1, 'split_utterances': False}
    t0 = time.time()
    resp = requests.post(HUME_TTS_URL, headers=headers, json=payload, timeout=90)
    elapsed = time.time() - t0
    if resp.status_code != 200:
        raise RuntimeError(f'TTS {resp.status_code}: {resp.text}')
    data = resp.json()
    gens = data.get('generations') or []
    if not gens or not gens[0].get('audio'):
        raise RuntimeError(f'Bad response: {data}')
    import base64
    audio_bytes = base64.b64decode(gens[0]['audio'])
    meta = {'request_id': data.get('request_id'), 'generation_id': gens[0].get('generation_id'), 'duration_s': float(gens[0].get('duration') or 0.0), 'encoding': gens[0].get('encoding'), 'file_size': gens[0].get('file_size'), 'elapsed_sec': round(elapsed, 3), 'model_version': '1', 'used_voice': voice_ref or None}
    return (payload, audio_bytes, meta)

class SynthApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('Synthetic Interview Data — Curation')
        self.geometry('1120x900')
        env = load_env(ENV_PATH)
        default_name = env.get('USER_NAME', '')
        default_key = env.get('HUME_API_KEY', '')
        self.answers = read_answers(ANSWERS_PATH)
        self.session_seed = random.randrange(1 << 31)
        self.rng = random.Random(self.session_seed)
        self.sample_seed_params = None
        self.sample_seed_instr = None
        self.sample_seed_answer = None
        self.params_edited = False
        self.user_name = tk.StringVar(value=default_name)
        self.api_key = tk.StringVar(value=default_key)
        self.target_minutes = tk.DoubleVar(value=12.0)
        self.generated_seconds = 0.0
        self.count_saved = {'negative': 0, 'positive': 0}
        self.current_label = 'negative'
        self.apply_aug = tk.BooleanVar(value=True)
        self.aug_intensity = tk.StringVar(value='auto')
        self.current_payload = None
        self.current_audio_bytes = None
        self.current_resp_meta = None
        self.current_priors = None
        self.current_answer_idx = None
        self.current_voice_ref = None
        self._preview_tmp = None
        self._preview_y = None
        self._preview_sr = None
        self._preview_aug_meta = None
        self._is_playing = False
        self._play_start_time = 0.0
        self._play_offset_s = 0.0
        self._player = None
        self._pcm16_buf = None
        self.track_total_s = 0.0
        self.track_pos_var = tk.DoubleVar(value=0.0)
        self._slider_dragging = False
        self._build_ui()
        self._update_progress()
        self._randomize_all_fresh()
        self.after(100, self._update_slider_loop)

    def _build_ui(self):
        top = ttk.LabelFrame(self, text='Operator & Target')
        top.pack(fill='x', padx=10, pady=8)
        ttk.Label(top, text='Your name:').grid(row=0, column=0, sticky='w', padx=6, pady=6)
        ttk.Entry(top, textvariable=self.user_name, width=24).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Label(top, text='Target minutes:').grid(row=0, column=2, sticky='w', padx=12)
        ttk.Entry(top, textvariable=self.target_minutes, width=8).grid(row=0, column=3, sticky='w', padx=6)
        ttk.Label(top, text='Hume API key:').grid(row=0, column=4, sticky='w', padx=12)
        ttk.Entry(top, textvariable=self.api_key, width=44, show='*').grid(row=0, column=5, sticky='w', padx=6)
        self.progress_lbl = ttk.Label(top, text='Progress: 00:00 / 00:00')
        self.progress_lbl.grid(row=0, column=6, sticky='e', padx=12)
        lab = ttk.LabelFrame(self, text='Label (auto 50/50)')
        lab.pack(fill='x', padx=10, pady=(0, 8))
        self.label_value = ttk.Label(lab, text='—')
        self.label_value.grid(row=0, column=0, sticky='w', padx=6, pady=6)
        ttk.Button(lab, text='Reroll All', command=self._randomize_all_fresh).grid(row=0, column=1, padx=12)
        prm = ttk.LabelFrame(self, text='Randomized Parameters (editable natural language)')
        prm.pack(fill='x', padx=10, pady=8)
        self.params_txt = tk.Text(prm, height=3, wrap='word')
        self.params_txt.grid(row=0, column=0, columnspan=6, sticky='nsew', padx=6, pady=6)
        prm.columnconfigure(5, weight=1)
        self.seed_label = ttk.Label(prm, text='Seed: —')
        self.seed_label.grid(row=1, column=0, sticky='w', padx=6, pady=(0, 6))
        ttk.Button(prm, text='Reroll Params', command=self._reroll_params).grid(row=1, column=1, sticky='w', padx=6, pady=(0, 6))

        def on_params_modified(event):
            if self.params_txt.edit_modified():
                self.params_edited = True
                self.seed_label.config(text='Seed: — (edited)')
                self.params_txt.edit_modified(False)
        self.params_txt.bind('<<Modified>>', on_params_modified)
        edit = ttk.LabelFrame(self, text='Instruction & Answer')
        edit.pack(fill='both', expand=True, padx=10, pady=8)
        ttk.Label(edit, text='Custom Instruction (acting only):').grid(row=0, column=0, sticky='w', padx=6, pady=(6, 0))
        self.instr_txt = tk.Text(edit, height=3, wrap='word')
        self.instr_txt.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=6)
        ttk.Button(edit, text='Reroll Instruction', command=self._reroll_instruction).grid(row=1, column=4, sticky='n', padx=6, pady=6)
        ttk.Label(edit, text='Answer Text:').grid(row=2, column=0, sticky='w', padx=6, pady=(6, 0))
        self.answer_txt = tk.Text(edit, height=8, wrap='word')
        self.answer_txt.grid(row=3, column=0, columnspan=4, sticky='nsew', padx=6, pady=(0, 6))
        ttk.Button(edit, text='Reroll Answer', command=self._reroll_answer).grid(row=3, column=4, sticky='n', padx=6, pady=6)
        edit.rowconfigure(1, weight=1)
        edit.rowconfigure(3, weight=2)
        edit.columnconfigure(3, weight=1)
        aug = ttk.LabelFrame(self, text='Augmentation')
        aug.pack(fill='x', padx=10, pady=8)
        ttk.Checkbutton(aug, text='Apply augmentation (recommended)', variable=self.apply_aug).grid(row=0, column=0, padx=6, pady=6, sticky='w')
        ttk.Label(aug, text='Intensity:').grid(row=0, column=1, sticky='e')
        ttk.Combobox(aug, textvariable=self.aug_intensity, values=['auto', 'low', 'med', 'high'], width=7).grid(row=0, column=2, sticky='w', padx=6)
        btn = ttk.Frame(self)
        btn.pack(fill='x', padx=10, pady=8)
        self.generate_btn = ttk.Button(btn, text='Generate', command=self._on_generate)
        self.generate_btn.pack(side='left')
        self.play_btn = ttk.Button(btn, text='Play', command=self._on_play, state='disabled')
        self.play_btn.pack(side='left', padx=8)
        self.stop_btn = ttk.Button(btn, text='Stop', command=self._on_stop, state='disabled')
        self.stop_btn.pack(side='left')
        self.retry_btn = ttk.Button(btn, text='Retry', command=self._on_retry, state='disabled')
        self.retry_btn.pack(side='left', padx=8)
        self.confirm_btn = ttk.Button(btn, text='Confirm & Save', command=self._on_confirm, state='disabled')
        self.confirm_btn.pack(side='left', padx=8)
        track = ttk.LabelFrame(self, text='Preview')
        track.pack(fill='x', padx=10, pady=(0, 10))
        self.time_lbl = ttk.Label(track, text='00:00 / 00:00')
        self.time_lbl.pack(side='left', padx=6)
        self.track_pos_var = tk.DoubleVar(value=0.0)
        self.track_scale = tk.Scale(track, from_=0.0, to=0.0, orient='horizontal', showvalue=False, resolution=0.01, length=820, variable=self.track_pos_var)
        self.track_scale.pack(side='left', padx=10, fill='x', expand=True)
        self.track_scale.bind('<Button-1>', self._on_slider_press)
        self.track_scale.bind('<B1-Motion>', self._on_slider_drag)
        self.track_scale.bind('<ButtonRelease-1>', self._on_slider_release)
        self.status_lbl = ttk.Label(self, text='Ready.')
        self.status_lbl.pack(fill='x', padx=10, pady=(0, 10))
        if not SOUNDDEV_OK and (not SIMPLEAUDIO_OK):
            set_status(self.status_lbl, 'sounddevice/simpleaudio not found — playback will open in system player. Install: pip install sounddevice simpleaudio', COLOR_ORANGE)

    def _choose_next_label(self) -> str:
        return 'negative' if self.count_saved['negative'] <= self.count_saved['positive'] else 'positive'

    def _prepare_preview_track(self, y: np.ndarray, sr: int):
        self._preview_y, self._preview_sr = (y, sr)
        self.track_total_s = 0.0 if y is None else len(y) / float(sr)
        self.track_scale.config(from_=0.0, to=max(self.track_total_s, 0.01))
        self.track_pos_var.set(0.0)
        self._play_offset_s = 0.0
        self._is_playing = False
        self.time_lbl.config(text=f'00:00 / {seconds_to_mmss(self.track_total_s)}')

    def _randomize_all_fresh(self):
        self._on_stop()
        self.current_label = self._choose_next_label()
        self.label_value.config(text=f'Current label: {self.current_label}')
        self.sample_seed_params = self.rng.randrange(1 << 32)
        self.sample_seed_instr = self.rng.randrange(1 << 32)
        self.sample_seed_answer = self.rng.randrange(1 << 32)
        self.params_edited = False
        rng_p = random.Random(self.sample_seed_params)
        pri = sample_all_priors(rng_p, label=self.current_label)
        self.current_priors = pri
        params_nl = short_parameters_text(pri, self.current_label)
        self.params_txt.delete('1.0', tk.END)
        self.params_txt.insert('1.0', params_nl)
        self.seed_label.config(text=f'Seed: {self.sample_seed_params}')
        rng_i = random.Random(self.sample_seed_instr)
        pool = NEGATIVE_INSTRUCTIONS if self.current_label == 'negative' else POSITIVE_INSTRUCTIONS
        instr = pool[rng_i.randrange(0, len(pool))]
        self.instr_txt.delete('1.0', tk.END)
        self.instr_txt.insert('1.0', instr)
        rng_a = random.Random(self.sample_seed_answer)
        self.current_answer_idx = rng_a.randrange(0, len(self.answers))
        ans = self.answers[self.current_answer_idx]
        self.answer_txt.delete('1.0', tk.END)
        self.answer_txt.insert('1.0', ans)
        self.current_payload = None
        self.current_audio_bytes = None
        self.current_resp_meta = None
        self.current_voice_ref = None
        self._preview_tmp = None
        self._preview_y = None
        self._preview_sr = None
        self._preview_aug_meta = None
        self._prepare_preview_track(np.zeros(1, dtype=np.float32), 48000)
        self.play_btn.config(state='disabled')
        self.stop_btn.config(state='disabled')
        self.retry_btn.config(state='disabled')
        self.confirm_btn.config(state='disabled')
        set_status(self.status_lbl, 'Randomized. Edit text if needed, then Generate.', COLOR_CYAN)

    def _reroll_params(self):
        self._on_stop()
        self.sample_seed_params = self.rng.randrange(1 << 32)
        rng_p = random.Random(self.sample_seed_params)
        pri = sample_all_priors(rng_p, label=self.current_label)
        self.current_priors = pri
        params_nl = short_parameters_text(pri, self.current_label)
        self.params_txt.delete('1.0', tk.END)
        self.params_txt.insert('1.0', params_nl)
        self.seed_label.config(text=f'Seed: {self.sample_seed_params}')
        self.params_edited = False

    def _reroll_instruction(self):
        self.sample_seed_instr = self.rng.randrange(1 << 32)
        rng_i = random.Random(self.sample_seed_instr)
        pool = NEGATIVE_INSTRUCTIONS if self.current_label == 'negative' else POSITIVE_INSTRUCTIONS
        instr = pool[rng_i.randrange(0, len(pool))]
        self.instr_txt.delete('1.0', tk.END)
        self.instr_txt.insert('1.0', instr)

    def _reroll_answer(self):
        self.sample_seed_answer = self.rng.randrange(1 << 32)
        rng_a = random.Random(self.sample_seed_answer)
        self.current_answer_idx = rng_a.randrange(0, len(self.answers))
        ans = self.answers[self.current_answer_idx]
        self.answer_txt.delete('1.0', tk.END)
        self.answer_txt.insert('1.0', ans)

    def _update_progress(self):
        tgt = max(0.0, float(self.target_minutes.get())) * 60.0
        cur = self.generated_seconds
        self.progress_lbl.config(text=f'Progress: {seconds_to_mmss(cur)} / {seconds_to_mmss(tgt)}')

    def _on_generate(self):
        name = self.user_name.get().strip()
        if not name:
            messagebox.showwarning('Missing name', 'Enter your name first.')
            return
        key = self.api_key.get().strip()
        if not key:
            messagebox.showwarning('Missing API key', 'Enter Hume API key.')
            return
        instruction = self.instr_txt.get('1.0', tk.END).strip()
        text = self.answer_txt.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning('Empty text', 'Answer text is empty.')
            return
        base_speed = float(self.current_priors.style_params['rate'])
        rng_local = random.Random(self.sample_seed_params)
        if self.current_label == 'negative':
            speed = min(1.4, max(1.1, base_speed * rng_local.uniform(1.05, 1.25)))
            trailing_silence = rng_local.uniform(0.02, 0.08)
        else:
            speed = min(1.15, max(0.9, base_speed * rng_local.uniform(0.9, 1.05)))
            trailing_silence = rng_local.uniform(0.2, 0.35)
        try:
            save_env(ENV_PATH, {'USER_NAME': name, 'HUME_API_KEY': key})
        except Exception:
            pass
        else:
            pass
        finally:
            pass
        self.generate_btn.config(state='disabled')
        set_status(self.status_lbl, 'Preparing voice…', COLOR_CYAN)
        identity_prompt = identity_prompt_from_priors(self.current_priors)

        def worker():
            try:
                voice_ref = ensure_voice(key, identity_prompt)
            except Exception:
                voice_ref = None
            else:
                pass
            finally:
                pass
            try:
                set_status(self.status_lbl, 'Generating…', COLOR_CYAN)
                payload, audio_bytes, meta = call_hume_tts(api_key=key, text=text, instruction=instruction, voice_ref=voice_ref, speed_hint=speed, trailing_silence=trailing_silence)
            except Exception as e:
                self.after(0, self._on_generate_done, e, None, None, None, None)
                return
            else:
                pass
            finally:
                pass
            self.after(0, self._on_generate_done, None, payload, audio_bytes, meta, voice_ref)
        threading.Thread(target=worker, daemon=True).start()

    def _on_generate_done(self, err, payload, audio_bytes, meta, voice_ref):
        self.generate_btn.config(state='normal')
        if err:
            set_status(self.status_lbl, f'Error: {err}', COLOR_RED)
            messagebox.showerror('Generation failed', str(err))
            return
        self.current_payload = payload
        self.current_audio_bytes = audio_bytes
        self.current_resp_meta = meta
        self.current_voice_ref = voice_ref
        tmp_dir = OUTPUT_ROOT / '_tmp_play'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        self._preview_tmp = tmp_dir / 'preview.mp3'
        self._preview_tmp.write_bytes(self.current_audio_bytes)
        try:
            y, sr = load_audio(str(self._preview_tmp), target_sr=48000)
        except Exception as e:
            set_status(self.status_lbl, f"Generated {meta.get('duration_s', 0.0):.2f}s. (Preview failed: {e})", COLOR_RED)
            self.play_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.retry_btn.config(state='normal')
            self.confirm_btn.config(state='normal')
            return
        else:
            pass
        finally:
            pass
        self._preview_aug_meta = None
        if self.apply_aug.get():
            try:
                cfg = AugmentConfig(intensity=self.aug_intensity.get(), rir_dir=None)
                aug_seed = (None if self.params_edited else self.sample_seed_params) or self.session_seed
                y_aug, applied, final_intensity = apply_augmentations(y, sr, seed=aug_seed, cfg=cfg)
                self._preview_aug_meta = {'seed': aug_seed, 'intensity': final_intensity, 'applied': applied, 'sr': sr, 'length_sec': round(len(y_aug) / sr, 3)}
                self._prepare_preview_track(y_aug, sr)
                set_status(self.status_lbl, f"Generated {meta.get('duration_s', 0.0):.2f}s. Playing (augmented)…", COLOR_CYAN)
            except Exception as e:
                self._prepare_preview_track(y, sr)
                set_status(self.status_lbl, f"Generated {meta.get('duration_s', 0.0):.2f}s. Playing (clean, augmentation failed: {e})…", COLOR_ORANGE)
            else:
                pass
            finally:
                pass
        else:
            self._prepare_preview_track(y, sr)
            set_status(self.status_lbl, f"Generated {meta.get('duration_s', 0.0):.2f}s. Playing…", COLOR_CYAN)
        self.play_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.retry_btn.config(state='normal')
        self.confirm_btn.config(state='normal')
        self._on_play()

    def _on_slider_press(self, _):
        self._slider_dragging = True

    def _on_slider_drag(self, _):
        pos = float(self.track_pos_var.get())
        self.time_lbl.config(text=f'{seconds_to_mmss(pos)} / {seconds_to_mmss(self.track_total_s)}')

    def _on_slider_release(self, _):
        self._slider_dragging = False
        self._on_seek(float(self.track_pos_var.get()))

    def _on_seek(self, new_pos_s: float):
        new_pos_s = max(0.0, min(self.track_total_s, new_pos_s))
        self._play_offset_s = new_pos_s
        self.time_lbl.config(text=f'{seconds_to_mmss(new_pos_s)} / {seconds_to_mmss(self.track_total_s)}')
        if self._is_playing:
            self._start_play_from_offset()

    def _start_play_from_offset(self):
        if self._preview_y is None or self._preview_sr is None:
            return
        if SOUNDDEV_OK:
            try:
                sd.stop()
            except Exception:
                pass
            else:
                pass
            finally:
                pass
        if SIMPLEAUDIO_OK and self._player:
            try:
                self._player.stop()
            except Exception:
                pass
            else:
                pass
            finally:
                pass
            self._player = None
        sr = self._preview_sr
        start_idx = int(self._play_offset_s * sr)
        start_idx = max(0, min(len(self._preview_y), start_idx))
        seg = self._preview_y[start_idx:]
        if len(seg) == 0:
            self._is_playing = False
            self.play_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            return
        if SOUNDDEV_OK:
            try:
                sd.play(seg, sr, blocking=False)
            except Exception:
                self._play_with_fallback(seg, sr)
            else:
                pass
            finally:
                pass
        elif SIMPLEAUDIO_OK:
            self._play_with_fallback(seg, sr)
        else:
            if self._preview_tmp:
                default_open_file(self._preview_tmp)
            return
        self._is_playing = True
        self._play_start_time = time.time()
        self.play_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

    def _play_with_fallback(self, y: np.ndarray, sr: int):
        if SIMPLEAUDIO_OK:
            try:
                x = np.clip(y, -1.0, 1.0)
                self._pcm16_buf = (x * 32767.0).astype(np.int16).tobytes()
                self._player = sa.play_buffer(self._pcm16_buf, 1, 2, sr)
            except Exception:
                if self._preview_tmp:
                    default_open_file(self._preview_tmp)
            else:
                pass
            finally:
                pass
        elif self._preview_tmp:
            default_open_file(self._preview_tmp)

    def _on_play(self):
        if self._preview_y is None:
            if self._preview_tmp:
                default_open_file(self._preview_tmp)
            return
        self._start_play_from_offset()

    def _on_stop(self):
        if self._is_playing:
            elapsed = time.time() - self._play_start_time
            self._play_offset_s = max(0.0, min(self.track_total_s, self._play_offset_s + elapsed))
        if SOUNDDEV_OK:
            try:
                sd.stop()
            except Exception:
                pass
            else:
                pass
            finally:
                pass
        if SIMPLEAUDIO_OK and getattr(self, '_player', None):
            try:
                self._player.stop()
            except Exception:
                pass
            else:
                pass
            finally:
                pass
            self._player = None
        self._is_playing = False
        self.play_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

    def _update_slider_loop(self):
        if self._preview_y is not None and (not self._slider_dragging):
            if self._is_playing:
                elapsed = time.time() - self._play_start_time
                pos = self._play_offset_s + elapsed
                if pos >= self.track_total_s - 0.001:
                    pos = self.track_total_s
                    self._is_playing = False
                    self.play_btn.config(state='normal')
                    self.stop_btn.config(state='disabled')
                self.track_pos_var.set(pos)
                self.time_lbl.config(text=f'{seconds_to_mmss(pos)} / {seconds_to_mmss(self.track_total_s)}')
            else:
                pos = float(self.track_pos_var.get())
                self.time_lbl.config(text=f'{seconds_to_mmss(pos)} / {seconds_to_mmss(self.track_total_s)}')
        self.after(100, self._update_slider_loop)

    def _on_retry(self):
        self._on_stop()
        self.current_payload = None
        self.current_audio_bytes = None
        self.current_resp_meta = None
        self.current_voice_ref = None
        self._preview_tmp = None
        self._preview_y = None
        self._preview_sr = None
        self._preview_aug_meta = None
        self.play_btn.config(state='disabled')
        self.stop_btn.config(state='disabled')
        self.retry_btn.config(state='disabled')
        self.confirm_btn.config(state='disabled')
        set_status(self.status_lbl, 'Discarded. Edit / reroll and Generate again.', COLOR_CYAN)

    def _on_confirm(self):
        if not all([self.current_payload, self.current_audio_bytes, self.current_resp_meta, self.current_priors]):
            messagebox.showwarning('Nothing to save', 'Generate something first.')
            return
        self._on_stop()
        user = self.user_name.get().strip() or 'user'
        key = self.api_key.get().strip()
        try:
            save_env(ENV_PATH, {'USER_NAME': user, 'HUME_API_KEY': key})
        except Exception:
            pass
        else:
            pass
        finally:
            pass
        label = self.current_label
        out_dir = OUTPUT_ROOT / user / label
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = unique_stem(user, label)
        mp3_path = out_dir / f'{stem}.mp3'
        mp3_path.write_bytes(self.current_audio_bytes)
        params_seed = None if self.params_edited else self.sample_seed_params
        metadata = {'session_seed': self.session_seed, 'seeds': {'parameters': params_seed, 'instruction': self.sample_seed_instr, 'answer': self.sample_seed_answer}, 'user': user, 'label': label, 'answer_index': int(self.current_answer_idx), 'answer_text': self.answer_txt.get('1.0', tk.END).strip(), 'instruction_text': self.instr_txt.get('1.0', tk.END).strip(), 'parameters_text': self.params_txt.get('1.0', tk.END).strip(), 'priors': {'gender': self.current_priors.gender, 'age': self.current_priors.age, 'accent': self.current_priors.accent, 'features': list(self.current_priors.features), 'style_params': dict(self.current_priors.style_params)}, 'voice_ref': self.current_voice_ref or None, 'hume_payload': self.current_payload, 'hume_response': self.current_resp_meta, 'paths': {'mp3': str(mp3_path)}, 'created_utc': datetime.utcnow().isoformat() + 'Z', 'version': 'synth_gui_structured_v1'}
        meta_path = out_dir / f'{stem}.json'
        meta_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        if self.apply_aug.get():
            try:
                if self._preview_aug_meta is not None and self._preview_y is not None:
                    aug_path = out_dir / f'{stem}_aug.wav'
                    save_wav(str(aug_path), self._preview_y, self._preview_sr)
                    aug_meta = dict(self._preview_aug_meta)
                    aug_meta.update({'input_path': str(mp3_path), 'output_path': str(aug_path)})
                else:
                    y, sr = load_audio(str(mp3_path), target_sr=48000)
                    cfg = AugmentConfig(intensity=self.aug_intensity.get(), rir_dir=None)
                    aug_seed = params_seed or self.session_seed
                    y_aug, applied, final_intensity = apply_augmentations(y, sr, seed=aug_seed, cfg=cfg)
                    aug_path = out_dir / f'{stem}_aug.wav'
                    save_wav(str(aug_path), y_aug, sr)
                    aug_meta = {'seed': aug_seed, 'intensity': final_intensity, 'applied': applied, 'sr': sr, 'length_sec': round(len(y_aug) / sr, 3), 'input_path': str(mp3_path), 'output_path': str(aug_path)}
                (out_dir / f'{stem}_aug.wav.json').write_text(json.dumps(aug_meta, indent=2), encoding='utf-8')
                metadata['paths']['aug_wav'] = str(aug_meta['output_path'])
                metadata['augmentation'] = aug_meta
                meta_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            except Exception as e:
                messagebox.showwarning('Augmentation failed', f'Saved MP3/JSON, but augmentation failed: {e}')
            else:
                pass
            finally:
                pass
        dur = float(self.current_resp_meta.get('duration_s') or 0.0)
        self.generated_seconds += dur
        self.count_saved[label] += 1
        self._update_progress()
        tgt_sec = max(0.0, float(self.target_minutes.get())) * 60.0
        if self.generated_seconds >= tgt_sec + OVERSHOOT_MARGIN_SEC:
            set_status(self.status_lbl, f'Saved. Target reached (≥ {seconds_to_mmss(tgt_sec)}).', COLOR_GREEN)
        else:
            set_status(self.status_lbl, 'Saved. Next sample randomized.', COLOR_GREEN)
            self._randomize_all_fresh()
if __name__ == '__main__':
    app = SynthApp()
    app.mainloop()
