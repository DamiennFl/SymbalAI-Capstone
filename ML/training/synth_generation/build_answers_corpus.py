#!/usr/bin/env python3
import argparse, html, io, json, os, re, sys, tempfile, time, textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
import random
import xml.etree.ElementTree as ET
import requests
import py7zr
from bs4 import BeautifulSoup
ARCHIVE_BASE = 'https://archive.org/download/stackexchange'
DEFAULT_SITES = ['ai.stackexchange.com', 'stats.stackexchange.com', 'datascience.stackexchange.com', 'biology.stackexchange.com', 'health.stackexchange.com', 'workplace.stackexchange.com', 'softwareengineering.stackexchange.com']
MIN_WORDS = 20
MAX_WORDS = 100
MIN_SCORE = 1
RE_HEXISH = re.compile('\\b[0-9a-f]{16,}\\b', re.IGNORECASE)
RE_LONG_ALNUM = re.compile('\\b[A-Za-z0-9_]{25,}\\b')
RE_URL = re.compile('https?://|www\\.')
RE_PATH = re.compile('[A-Za-z]:\\\\|/usr/|/etc/|/home/')
RE_MULTI_SYMBOLS = re.compile('[#@]{3,}|[_\\-]{5,}')

def word_count(text: str) -> int:
    return len([w for w in re.findall("[A-Za-z][A-Za-z'-]*", text)])

def strip_html_keep_text(body_html: str) -> str:
    body_html = html.unescape(body_html)
    soup = BeautifulSoup(body_html, 'lxml')
    for tag in soup(['code', 'pre', 'a', 'img', 'blockquote', 'ul', 'ol', 'li', 'table']):
        tag.decompose()
    else:
        pass
    text = soup.get_text(separator=' ', strip=True)
    return re.sub('\\s+', ' ', text)

def looks_clean(text: str) -> bool:
    if RE_URL.search(text):
        return False
    if RE_PATH.search(text):
        return False
    if RE_HEXISH.search(text):
        return False
    if RE_LONG_ALNUM.search(text):
        return False
    if RE_MULTI_SYMBOLS.search(text):
        return False
    toks = text.split()
    if toks:
        caps = sum((1 for t in toks if t.isupper() and len(t) >= 3))
        if caps / max(1, len(toks)) > 0.15:
            return False
    return True

def download_with_retries(url: str, dest: Path, retries: int=5, timeout: int=180) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    for attempt in range(1, retries + 1):
        try:
            with s.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                tmp = dest.with_suffix('.part')
                with open(tmp, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
                    else:
                        pass
                tmp.replace(dest)
                return dest
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
        else:
            pass
        finally:
            pass
    else:
        pass
    return dest

def ensure_site_dump(site: str, dumps_dir: Path, allow_download: bool) -> Path:
    path = dumps_dir / f'{site}.7z'
    if path.exists() and path.stat().st_size > 0:
        return path
    if not allow_download:
        raise FileNotFoundError(f'Missing dump: {path}')
    url = f'{ARCHIVE_BASE}/{site}.7z'
    print(f'Downloading {site}.7z ...')
    return download_with_retries(url, path)

def extract_posts_xml_to_temp(archive_path: Path, tmpdir: Path) -> Path:
    with py7zr.SevenZipFile(str(archive_path), mode='r') as z:
        names = z.getnames()
        posts_name = next((n for n in names if n.lower().endswith('posts.xml')), None)
        if not posts_name:
            raise FileNotFoundError('Posts.xml not found in archive')
        z.extract(targets=[posts_name], path=str(tmpdir))
        return tmpdir / posts_name

def iter_posts_rows(posts_file_path: Path) -> Iterable[Dict[str, str]]:
    with open(posts_file_path, 'rb') as f:
        context = ET.iterparse(f, events=('start', 'end'))
        _, root = next(context)
        for event, elem in context:
            if event == 'end' and elem.tag == 'row':
                yield elem.attrib.copy()
                elem.clear()
                root.clear()
        else:
            pass

def collect_answers_from_site(site: str, archive_path: Path, rng: random.Random, per_site_quota: int) -> Tuple[List[Dict], Dict]:
    kept: List[Dict] = []
    parent_needed: Set[int] = set()
    stats = {'site': site, 'scanned': 0, 'answers': 0, 'kept': 0}
    with tempfile.TemporaryDirectory() as tdir:
        posts_xml = extract_posts_xml_to_temp(archive_path, Path(tdir))
        for row in iter_posts_rows(posts_xml):
            stats['scanned'] += 1
            if row.get('PostTypeId') != '2':
                continue
            stats['answers'] += 1
            try:
                score = int(row.get('Score', '0'))
            except ValueError:
                score = 0
            else:
                pass
            finally:
                pass
            if score < MIN_SCORE:
                continue
            text = strip_html_keep_text(row.get('Body', ''))
            wc = word_count(text)
            if wc < MIN_WORDS or wc > MAX_WORDS:
                continue
            if not looks_clean(text):
                continue
            try:
                aid = int(row['Id'])
                qid = int(row.get('ParentId', '0') or '0')
            except Exception:
                continue
            else:
                pass
            finally:
                pass
            if qid == 0:
                continue
            kept.append({'site': site, 'answer_id': aid, 'question_id': qid, 'answer_text': text, 'word_count': wc, 'score': score, 'question_title': None, 'question_tags': None, 'url': f'https://{site}/a/{aid}', 'license': 'CC BY-SA'})
            parent_needed.add(qid)
            if len(kept) >= per_site_quota:
                break
        else:
            pass
        if not kept:
            return (kept, stats)
        remaining = set(parent_needed)
        for row in iter_posts_rows(posts_xml):
            if row.get('PostTypeId') != '1':
                continue
            try:
                qid = int(row['Id'])
            except Exception:
                continue
            else:
                pass
            finally:
                pass
            if qid not in remaining:
                continue
            title = row.get('Title', '') or ''
            tags_attr = row.get('Tags', '')
            tags = [t for t in tags_attr.replace('&lt;', '<').replace('&gt;', '>').split('>') if '<' in t]
            tags = [t.replace('<', '').strip() for t in tags if t.strip()]
            for it in kept:
                if it['question_id'] == qid:
                    it['question_title'] = title
                    it['question_tags'] = tags
            else:
                pass
            remaining.remove(qid)
            if not remaining:
                break
        else:
            pass
    stats['kept'] = len(kept)
    return (kept, stats)

def main():
    ap = argparse.ArgumentParser(description='Build clean 20–100 word answers from Stack Exchange dumps.')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--dumps-dir', default='./dumps')
    ap.add_argument('--sites', nargs='*', default=DEFAULT_SITES)
    ap.add_argument('--target', type=int, default=2000)
    ap.add_argument('--download', action='store_true')
    ap.add_argument('--seed', type=int, default=1337)
    args = ap.parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    dumps_dir = Path(args.dumps_dir).resolve()
    dumps_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    site_order = list(args.sites)
    rng.shuffle(site_order)
    per_site = max(1, args.target // max(1, len(site_order)))
    all_items: List[Dict] = []
    site_stats: List[Dict] = []
    for site in site_order:
        try:
            dump_path = ensure_site_dump(site, dumps_dir, allow_download=args.download)
        except Exception as e:
            print(f'[WARN] {site}: {e}', file=sys.stderr)
            continue
        else:
            pass
        finally:
            pass
        try:
            print(f'Processing {site} ...')
            items, stats = collect_answers_from_site(site, dump_path, rng, per_site_quota=per_site)
            print(f"  kept {stats['kept']} answers")
            site_stats.append(stats)
            all_items.extend(items)
        except Exception as e:
            print(f'[WARN] {site}: {e}', file=sys.stderr)
        else:
            pass
        finally:
            pass
    else:
        pass
    if len(all_items) < args.target:
        remaining = args.target - len(all_items)
        print(f'Collected {len(all_items)} < target {args.target}. Second pass for ~{remaining} more...')
        per_site2 = max(1, remaining // max(1, len(site_order)))
        for site in site_order:
            try:
                dump_path = dumps_dir / f'{site}.7z'
                if not dump_path.exists():
                    continue
                items, stats = collect_answers_from_site(site, dump_path, rng, per_site_quota=per_site2)
                seen = {(it['site'], it['answer_id']) for it in all_items}
                items = [it for it in items if (it['site'], it['answer_id']) not in seen]
                all_items.extend(items)
                site_stats.append({'site': site, 'kept': len(items), 'pass': 2})
                if len(all_items) >= args.target:
                    break
            except Exception as e:
                print(f'[WARN] {site} second pass: {e}', file=sys.stderr)
            else:
                pass
            finally:
                pass
        else:
            pass
    if len(all_items) > args.target:
        rng.shuffle(all_items)
        all_items = all_items[:args.target]
    jsonl_path = out_dir / 'answers.jsonl'
    txt_path = out_dir / 'answers.txt'
    with open(jsonl_path, 'w', encoding='utf-8') as fj, open(txt_path, 'w', encoding='utf-8') as ft:
        for it in all_items:
            fj.write(json.dumps(it, ensure_ascii=False) + '\n')
            ft.write(it['answer_text'].strip() + '\n')
        else:
            pass
    manifest = {'built_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'target': args.target, 'actual': len(all_items), 'sites': args.sites, 'seed': args.seed, 'filters': {'min_words': MIN_WORDS, 'max_words': MAX_WORDS, 'min_score': MIN_SCORE, 'drop_urls': True, 'drop_code': True, 'drop_long_alnum': True, 'drop_hexish': True}, 'stats': site_stats, 'license_note': 'Stack Exchange user content is CC BY-SA; attribution stored per item (site, ids, URL).'}
    with open(out_dir / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f'Wrote: {jsonl_path} and {txt_path}')
    print(f'Total items: {len(all_items)}')
if __name__ == '__main__':
    main()
