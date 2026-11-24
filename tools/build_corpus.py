#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ساخت پیکرهٔ برچسب‌خورده از دادهٔ عمومی گنجور (ganjoor-data).

منبع برچسب‌ها: برچسب‌های تأییدشدهٔ انسانیِ گنجور روی ابیات.
  - PersonMention = Allusion  → بیت دارای تلمیح (مثبت)
  - PersonMention = Participant → نام در بیت هست ولی بخشی از روایت است، نه تلمیح (منفی سخت)

هر بیت فقط یک بار در پیکره می‌آید و تقسیم train/val/test بر اساس شناسهٔ شعر انجام می‌شود
تا بیت‌های یک شعر هرگز بین بخش‌ها پخش نشوند (جلوگیری از نشت داده).
"""
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys
import urllib.request

BASE = 'https://cdn.jsdelivr.net/gh/ganjoor/ganjoor-data@main/'
RAW = 'https://raw.githubusercontent.com/ganjoor/ganjoor-data/main/'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(HERE, 'ganjoor_raw')
OUT = os.path.join(HERE, 'corpus', 'ganjoor_labeled.jsonl')
BUCKET = 2000


def fetch_json(path, base=BASE):
    req = urllib.request.Request(base + path, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def load_person_tags():
    """{poem_id: {couplet_index: [(person_id, mention), ...]}}"""
    tags = collections.defaultdict(lambda: collections.defaultdict(list))
    for shard in (0, 1):
        path = os.path.join(RAW_DIR, f'person-tags-{shard}.json')
        if not os.path.exists(path):
            continue
        data = json.load(open(path, encoding='utf-8'))
        for pid, items in data.items():
            for it in items:
                tags[it['PoemId']][it['CoupletIndex']].append((int(pid), it['PersonMention']))
    return tags


def poem_url_index(needed_ids):
    """فقط شناسه‌های لازم را از شاردهای ایندکس می‌گیرد (بدون ذخیرهٔ کل ایندکس)."""
    needed = set(needed_ids)
    buckets = sorted({i // BUCKET for i in needed})
    found = {}
    for b in buckets:
        path = f'index/poems-by-id/{b}.json'
        data = None
        for base in (BASE, RAW):
            try:
                data = fetch_json(path, base)
                break
            except Exception as e:  # noqa: BLE001
                last = e
        if data is None:
            print(f'  ! شارد {b} دریافت نشد: {last}', file=sys.stderr)
            continue
        for k, v in data.items():
            ki = int(k)
            if ki in needed:
                found[ki] = v
    return found


NARRATIVE_VERBS = {
    'گفت', 'کرد', 'شد', 'رفت', 'امد', 'آمد', 'داد', 'گرفت', 'زد', 'کشت', 'بست',
    'رهاند', 'سپرد', 'فرستاد', 'خواند', 'نوشت', 'دید', 'شنید', 'برخاست', 'نشست',
    'پرسید', 'فرمود', 'ببرد', 'بیاورد', 'بگرفت', 'بکشت', 'برفت', 'بیامد', 'بداد',
    'بزد', 'ببست', 'برخاست', 'بشد', 'بگفت', 'نهاد', 'افکند', 'کشید', 'برداشت',
}


def poem_features(poem):
    """ویژگی‌های سطح شعر: تعداد بیت و نسبت بیت‌های روایی."""
    cs = couplets_of(poem)
    n = len(cs) or 1
    narr = 0
    for _, m1, m2 in cs:
        ws = set(re.findall(r'[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]+', m1 + ' ' + m2))
        if ws & NARRATIVE_VERBS:
            narr += 1
    return {'poem_len': len(cs), 'narrative_ratio': round(narr / n, 3)}


def split_lines(plain):
    return [ln.strip() for ln in str(plain).replace('\r\n', '\n').replace('\r', '\n').split('\n')
            if ln.strip()]


def couplets_of(poem):
    """[(index, misra1, misra2)] — شمارهٔ بیت در کل شعر (همان شمارهٔ Verses در گنجور)."""
    out = []
    n = 0
    for sec in poem.get('Sections') or []:
        lines = split_lines(sec.get('PlainText') or '')
        for i in range(0, len(lines) - 1, 2):
            out.append((n, lines[i], lines[i + 1]))
            n += 1
    return out


def poet_of(poem):
    title = poem.get('FullTitle') or ''
    return title.split(' » ')[0].strip() if ' » ' in title else ''


CACHE = os.path.join(RAW_DIR, 'poems')


def fetch_poem(poem_id, url):
    # قالب گنجور: poets/{poetSlug}/{catPath}/{poemSlug}.json  و FullUrl = /{poetSlug}/{...}
    path = os.path.join(CACHE, f'{poem_id}.json')
    if os.path.exists(path) and os.path.getsize(path) > 40:
        try:
            return poem_id, json.load(open(path, encoding='utf-8'))
        except Exception:  # noqa: BLE001
            pass
    poem = fetch_json('poets' + url.rstrip('/') + '.json')
    os.makedirs(CACHE, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(poem, f, ensure_ascii=False)
    return poem_id, poem


def main():
    tags = load_person_tags()
    people = {p['Id']: p['Name'] for p in json.load(open(os.path.join(RAW_DIR, 'people.json'), encoding='utf-8'))}
    entity_counts = {
        pid: collections.Counter(people.get(p, str(p)) for ci in by_ci for p, _ in by_ci[ci])
        for pid, by_ci in tags.items()
    }
    ids = sorted(tags)
    print(f'شعرهای دارای برچسب: {len(ids)}')
    urls = poem_url_index(ids)
    print(f'نشانی یافت‌شده: {len(urls)}')
    todo = [(i, urls[i]) for i in ids if i in urls]

    rows = []
    untagged = []
    failed = []
    UNTAGGED_CAP = 1500
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_poem, i, u): i for i, u in todo}
        for n, fut in enumerate(cf.as_completed(futs), 1):
            try:
                pid, poem = fut.result()
            except Exception as e:  # noqa: BLE001
                failed.append((futs[fut], str(e)))
                continue
            poet = poet_of(poem)
            full_title = poem.get('FullTitle') or ''
            url = poem.get('FullUrl') or ''
            meta = poem_features(poem)
            meta['entity_counts'] = dict(entity_counts.get(pid, {}))
            for ci, m1, m2 in couplets_of(poem):
                mentions = tags[pid].get(ci)
                if not mentions:
                    # تیر دوم: ابیات بدون برچسب تلمیح، فقط برای سنجش هشدار کاذب.
                    # این‌ها برچسب قطعی «فاقد تلمیح» ندارند و در آزمون اصلی حساب نمی‌شوند.
                    if len(untagged) < UNTAGGED_CAP and len(m1) + len(m2) > 30:
                        untagged.append({
                            'id': f'{pid}:{ci}',
                            'text': m1 + ' / ' + m2,
                            'label': 0,
                            'label_source': 'ganjoor_untagged',
                            'persons': [],
                            'mentions': [],
                            'poem_id': pid,
                            'poem_title': full_title,
                            'poet': poet,
                            'couplet_index': ci,
                            'url': 'https://ganjoor.net' + url,
                            'poem_meta': meta,
                        })
                    continue
                label = 1 if any(m == 'Allusion' for _, m in mentions) else 0
                rows.append({
                    'id': f'{pid}:{ci}',
                    'text': m1 + ' / ' + m2,
                    'label': label,
                    'label_source': 'ganjoor_approved_person_tag',
                    'persons': sorted({p for p, _ in mentions}),
                    'mentions': sorted({m for _, m in mentions}),
                    'poem_id': pid,
                    'poem_title': full_title,
                    'poet': poet,
                    'couplet_index': ci,
                    'url': 'https://ganjoor.net' + url,
                    'poem_meta': meta,
                })
            if n % 100 == 0:
                print(f'  {n}/{len(todo)} شعر — {len(rows)} بیت', flush=True)

    # یکتا کردن بر اساس متن بیت (حذف تکرار واقعی، نه پر کردن عدد)
    seen, uniq = set(), []
    for r in rows:
        key = r['text']
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    # تقسیم بر اساس شعر، با تفکیک برچسب در هر شعر
    poet_groups = collections.defaultdict(list)
    for r in uniq:
        poet_groups[r['poet'] or '?'].append(r['poem_id'])
    poem_split = {}
    for poet, pids in poet_groups.items():
        for pid in sorted(set(pids)):
            h = int(hashlib.md5(f'{poet}|{pid}'.encode()).hexdigest()[:8], 16) % 100
            poem_split[pid] = 'test' if h < 20 else ('val' if h < 35 else 'train')
    for r in uniq:
        r['split'] = poem_split[r['poem_id']]

    # ابیات بدون برچسب فقط برای بخش آموزش/اعتبارسنجی (نه آزمون)
    for r in untagged:
        if r['text'] in seen:
            continue
        seen.add(r['text'])
        r['split'] = 'val' if poem_split.get(r['poem_id']) == 'test' else poem_split.get(r['poem_id'], 'train')
        if r['split'] == 'test':
            r['split'] = 'val'
        uniq.append(r)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        for r in uniq:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    c = collections.Counter((r['split'], r['label']) for r in uniq)
    print(f'\nنوشته شد: {OUT}')
    print(f'کل بیت یکتا: {len(uniq)}  (خام: {len(rows)})')
    for s in ('train', 'val', 'test'):
        print(f'  {s}: مثبت={c[(s, 1)]}  منفی={c[(s, 0)]}')
    print(f'شاعران: {len({r["poet"] for r in uniq})}')
    if failed:
        print(f'شعرهای ناموفق: {len(failed)}')


if __name__ == '__main__':
    main()
