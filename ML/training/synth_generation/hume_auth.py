#!/usr/bin/env python3
import argparse, base64, json, os, sys, time
from pathlib import Path
from typing import Optional, Tuple
import requests
TTS_URL = 'https://api.hume.ai/v0/tts'
TOKEN_URL = 'https://api.hume.ai/oauth2-cc/token'

def get_env(key: str, prompt: str) -> str:
    val = os.environ.get(key)
    if val:
        return val.strip()
    try:
        return input(f'{prompt}: ').strip()
    except KeyboardInterrupt:
        print('\nAborted.')
        sys.exit(1)
    else:
        pass
    finally:
        pass

def get_access_token(api_key: str, secret_key: str, timeout: int=30) -> str:
    resp = requests.post(TOKEN_URL, auth=(api_key, secret_key), data={'grant_type': 'client_credentials'}, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f'Token request failed {resp.status_code}: {resp.text}')
    data = resp.json()
    tok = data.get('access_token')
    if not tok:
        raise RuntimeError(f'No access_token in response: {data}')
    return tok

def synthesize_tts(text: str, description: Optional[str], api_key: Optional[str]=None, access_token: Optional[str]=None, sample_rate: int=48000, timeout: int=120) -> Tuple[bytes, dict]:
    if not api_key and (not access_token):
        raise ValueError('Provide api_key or access_token')
    headers = {'Accept': 'application/json; charset=utf-8'}
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    else:
        headers['X-Hume-Api-Key'] = api_key
    payload = {'utterances': [{'text': text, **({'description': description} if description else {}), 'speed': 1.0, 'trailing_silence': 0.2}], 'format': {'type': 'mp3'}, 'num_generations': 1, 'split_utterances': False}
    t0 = time.time()
    resp = requests.post(TTS_URL, headers=headers, json=payload, timeout=timeout)
    elapsed = time.time() - t0
    if resp.status_code != 200:
        raise RuntimeError(f'TTS failed {resp.status_code}: {resp.text}')
    data = resp.json()
    gens = data.get('generations') or []
    if not gens:
        raise RuntimeError(f'No generations in response: {data}')
    g0 = gens[0]
    b64 = g0.get('audio')
    if not b64:
        raise RuntimeError(f'No base64 audio in generation: {g0}')
    audio = base64.b64decode(b64)
    meta = {'request_id': data.get('request_id'), 'generation_id': g0.get('generation_id'), 'duration': g0.get('duration'), 'encoding': g0.get('encoding'), 'file_size': g0.get('file_size'), 'elapsed_sec': round(elapsed, 3)}
    return (audio, meta)

def main():
    ap = argparse.ArgumentParser(description='Hume auth + quick TTS check')
    ap.add_argument('--use-token', action='store_true', help='Use OAuth access token (needs HUME_SECRET_KEY)')
    ap.add_argument('--out', default='auth_check.mp3', help='Output file path')
    ap.add_argument('--text', default='This is a short authorization test for Hume text to speech.', help='Text to synthesize')
    ap.add_argument('--desc', default='Neutral test read; clear enunciation; no special style.', help='Acting instructions (description)')
    ap.add_argument('--rate', type=int, default=48000, help='MP3 sample rate')
    ap.add_argument('--timeout', type=int, default=120, help='HTTP timeout (s)')
    args = ap.parse_args()
    api_key = None
    access_token = None
    if args.use_token:
        api_key = get_env('HUME_API_KEY', 'Enter Hume API key')
        secret = get_env('HUME_SECRET_KEY', 'Enter Hume Secret key')
        print('Requesting access token...')
        access_token = get_access_token(api_key, secret, timeout=args.timeout)
        print('Got access token.')
    else:
        api_key = get_env('HUME_API_KEY', 'Enter Hume API key')
    print('Calling /v0/tts ...')
    audio, meta = synthesize_tts(text=args.text, description=args.desc, api_key=api_key, access_token=access_token, sample_rate=args.rate, timeout=args.timeout)
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    print('=== Hume TTS check ===')
    print(json.dumps(meta, indent=2))
    print(f'Saved: {out_path}  ({len(audio)} bytes)')
if __name__ == '__main__':
    main()
