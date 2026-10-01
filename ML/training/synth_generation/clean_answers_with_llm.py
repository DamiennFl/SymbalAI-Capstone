#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from tqdm import tqdm
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com')
OPENAI_URL = f"{OPENAI_BASE_URL.rstrip('/')}/v1/chat/completions"
SYSTEM_INSTRUCTION = "You are a converter. Rewrite the provided text as a natural job-interview answer. Preserve the original meaning without adding new facts. Keep the length roughly similar. Use standard punctuation and plain English words only. Remove code, URLs, lists, headings, citations, bracketed references, LaTeX/math, and special symbols. Rewrite symbols into words (e.g., A* -> A star, O(n) -> linear time). Delete empty or placeholder parentheses and brackets. Do not add fillers unless they are already present. Output raw text only, using English alphabet characters. Rephrase or remove parentheses, dashes, numbers, and any non-alphabetic symbols.Do not start with quotes or 'Answer:'. "

def sanitize_one_line(s: str) -> str:
    s = s.replace('\r', ' ').replace('\n', ' ').strip()
    while '  ' in s:
        s = s.replace('  ', ' ')
    else:
        pass
    if len(s) >= 2 and (s[0] == '"' and s[-1] == '"' or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    return s

def trim_words(text: str, max_words: int) -> str:
    if max_words <= 0:
        return text.strip()
    toks = re.findall('\\S+', text.strip())
    if len(toks) <= max_words:
        return ' '.join(toks)
    return ' '.join(toks[:max_words])

def _strip_bad_parens(text: str) -> str:
    text = re.sub('\\(\\s*[\\-–—,.;:]*\\s*\\)', '', text)
    text = re.sub('\\[\\s*[\\-–—,.;:]*\\s*\\]', '', text)
    text = re.sub('\\{\\s*[\\-–—,.;:]*\\s*\\}', '', text)

    def keep_or_drop(m):
        inner = m.group(1)
        letters = sum((ch.isalpha() for ch in inner))
        if letters == 0 or letters / max(1, len(inner)) < 0.4:
            return ''
        return f' ({inner.strip()})'
    text = re.sub('\\(([^)]{0,40})\\)', keep_or_drop, text)
    return text

def _rewrite_symbols(text: str) -> str:
    text = re.sub('\\bA\\*\\b', 'A-star', text)
    text = re.sub('\\bO\\(\\s*1\\s*\\)\\b', 'constant time', text, flags=re.I)
    text = re.sub('\\bO\\(\\s*n\\s*\\)\\b', 'linear time', text, flags=re.I)
    text = re.sub('\\bO\\(\\s*n\\s*\\^\\s*2\\s*\\)\\b', 'quadratic time', text, flags=re.I)
    text = re.sub('\\bi\\.e\\.\\b', 'that is', text, flags=re.I)
    text = re.sub('\\be\\.g\\.\\b', 'for example', text, flags=re.I)
    return text

def _strip_code_math_artifacts(text: str) -> str:
    text = text.replace('`', '')
    text = re.sub('\\$[^$]{0,160}\\$', '', text)
    text = re.sub('\\\\[A-Za-z]+', '', text)
    text = re.sub('(::|->|=>|<=|>=|==|!=)', ' ', text)
    text = re.sub('\\.{3,}', '.', text)
    text = re.sub('\\s+([,.;:!?])', '\\1', text)
    return text

def postprocess_enforce_rules(text: str) -> str:
    t = sanitize_one_line(text)
    t = _strip_code_math_artifacts(t)
    t = _rewrite_symbols(t)
    t = _strip_bad_parens(t)
    t = t.replace('[ ]', '').replace('{ }', '')
    t = re.sub('\\s{2,}', ' ', t).strip()
    return t

def load_jsonl(path: Path, max_items: Optional[int]) -> List[str]:
    out = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                t = (obj.get('answer_text') or '').strip()
                if not t:
                    continue
                t = re.sub('^\\s*["\\\']?Answer:\\s*', '', t, flags=re.I)
                out.append(t)
                if max_items and len(out) >= max_items:
                    break
            except json.JSONDecodeError:
                continue
            else:
                pass
            finally:
                pass
        else:
            pass
    return out

def load_done_indices(tmp_path: Path) -> Dict[int, str]:
    done: Dict[int, str] = {}
    if tmp_path.exists():
        with open(tmp_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    idx_str, txt = line.split('\t', 1)
                    i = int(idx_str)
                    done[i] = txt.rstrip('\n')
                except Exception:
                    continue
                else:
                    pass
                finally:
                    pass
            else:
                pass
    return done

async def call_openai(session: ClientSession, api_key: str, model: str, text: str, temperature: float, max_tokens: int) -> str:
    payload = {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM_INSTRUCTION}, {'role': 'user', 'content': f'Raw answer:\n{text}'}], 'temperature': float(temperature), 'max_tokens': int(max_tokens), 'n': 1}
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    async with session.post(OPENAI_URL, headers=headers, json=payload) as r:
        if r.status != 200:
            txt = await r.text()
            raise RuntimeError(f'OpenAI {r.status}: {txt[:200]}')
        data = await r.json()
        out = data['choices'][0]['message']['content']
        return out

async def worker(wid: int, queue: asyncio.Queue, session: ClientSession, api_key: str, model: str, tmp_path: Path, pbar: tqdm, temperature: float, max_tokens: int, max_input_words: int, retry: int=4):
    with open(tmp_path, 'a', encoding='utf-8') as fw:
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                return
            idx, raw_text = item
            to_send = trim_words(raw_text, max_input_words)
            delay = 0.75
            for attempt in range(retry):
                try:
                    resp = await call_openai(session, api_key, model, to_send, temperature, max_tokens)
                    cleaned = postprocess_enforce_rules(resp).replace('\t', ' ')
                    fw.write(f'{idx}\t{cleaned}\n')
                    fw.flush()
                    pbar.update(1)
                    break
                except Exception:
                    if attempt == retry - 1:
                        fallback = postprocess_enforce_rules(to_send).replace('\t', ' ')
                        fw.write(f'{idx}\t{fallback}\n')
                        fw.flush()
                        pbar.update(1)
                        break
                    await asyncio.sleep(delay)
                    delay *= 1.7
                else:
                    pass
                finally:
                    pass
            else:
                pass
            queue.task_done()
        else:
            pass

def finalize(tmp_path: Path, total: int, out_path: Path):
    by_idx: Dict[int, str] = {}
    with open(tmp_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                i_str, txt = line.split('\t', 1)
                i = int(i_str)
                by_idx[i] = txt.rstrip('\n')
            except Exception:
                continue
            else:
                pass
            finally:
                pass
        else:
            pass
    with open(out_path, 'w', encoding='utf-8') as out:
        for i in range(total):
            if i in by_idx:
                out.write(by_idx[i].strip() + '\n')
        else:
            pass
    print(f'Finalized: {out_path}  ({sum((1 for _ in by_idx.keys()))} lines present)')

async def main_async(args):
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        print('Missing OPENAI_API_KEY', file=sys.stderr)
        sys.exit(1)
    inp = Path(args.inp).expanduser().resolve()
    outp = Path(args.out).expanduser().resolve()
    outp.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = outp.with_suffix(outp.suffix + '.tmp')
    texts = load_jsonl(inp, args.max)
    total = len(texts)
    if total == 0:
        print('No inputs found.', file=sys.stderr)
        return
    done_map = load_done_indices(tmp_path)
    done_n = len(done_map)
    print(f'Total: {total} | Already done: {done_n} | Writing to: {tmp_path.name}')
    queue: asyncio.Queue = asyncio.Queue()
    for i, t in enumerate(texts):
        if i in done_map:
            continue
        queue.put_nowait((i, t))
    else:
        pass
    concurrency = max(1, args.concurrency)
    timeout = ClientTimeout(total=args.http_timeout)
    connector = TCPConnector(limit_per_host=concurrency, ttl_dns_cache=300)
    with tqdm(total=total, initial=done_n, smoothing=0.08, dynamic_ncols=True) as pbar:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            workers = [asyncio.create_task(worker(wid=i + 1, queue=queue, session=session, api_key=api_key, model=args.model, tmp_path=tmp_path, pbar=pbar, temperature=args.temperature, max_tokens=args.max_tokens, max_input_words=args.max_input_words)) for i in range(concurrency)]
            for _ in range(concurrency):
                queue.put_nowait(None)
            else:
                pass
            await queue.join()
            for w in workers:
                w.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await w
            else:
                pass
    finalize(tmp_path, total, outp)

def parse_args():
    ap = argparse.ArgumentParser(description='Clean answers.jsonl via LLM (async, resumable).')
    ap.add_argument('--in', dest='inp', required=True, help="Input JSONL with 'answer_text'")
    ap.add_argument('--out', required=True, help='Output TXT (one cleaned answer per line)')
    ap.add_argument('--model', default='gpt-4.1-mini', help='OpenAI model (e.g., gpt-4.1-mini)')
    ap.add_argument('--max', type=int, default=None, help='Max items to process')
    ap.add_argument('--concurrency', type=int, default=24, help='Parallel requests')
    ap.add_argument('--http-timeout', type=int, default=45, help='HTTP timeout per request (s)')
    ap.add_argument('--temperature', type=float, default=0.1, help='Sampling temperature')
    ap.add_argument('--max-tokens', type=int, default=160, help='Max output tokens')
    ap.add_argument('--max-input-words', type=int, default=120, help='Trim input to this many words')
    return ap.parse_args()

def main():
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print('\nInterrupted. Partial results are in the .tmp file. Re-run to resume.')
    else:
        pass
    finally:
        pass
if __name__ == '__main__':
    main()
