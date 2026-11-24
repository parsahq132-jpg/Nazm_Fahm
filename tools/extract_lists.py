#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""استخراج فهرست‌های واژگانی نسخهٔ اولیه به فایل‌های داده (resources/)."""
import ast
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, 'resources')
src = open(os.path.join(HERE, 'TheORIGINAL.py'), encoding='utf-8').read()


def literal(name, stop=None):
    start = src.find(f'\n{name} = ')
    if start < 0:
        start = src.find(f'{name} = ')
    end = stop if stop else len(src)
    block = src[start:end]
    # تا پایان عبارت: نخستین خط که با ) یا ] در ستون صفر شروع شود
    m = re.search(r'\n(?=[A-Z_]|\ndef |\nclass )', block[1:])
    if m:
        block = block[:m.start() + 1]
    body = block.split('=', 1)[1]
    body = re.sub(r'W\(\s*"([^"]*)"\s*\)', r'"\1"', body)
    body = re.sub(r"W\(\s*'([^']*)'\s*\)", r'"\1"', body)
    body = re.sub(r'\bW\(', '(', body)
    try:
        return ast.literal_eval(body.strip())
    except Exception as e:  # noqa: BLE001
        print(f'  ! {name}: {e}')
        return None


os.makedirs(RES, exist_ok=True)

stop = literal('STOP')
if stop:
    open(os.path.join(RES, 'stopwords.txt'), 'w', encoding='utf-8').write('\n'.join(sorted(stop)))

images = literal('IMAGES')
if images:
    open(os.path.join(RES, 'images.txt'), 'w', encoding='utf-8').write('\n'.join(sorted(images)))

fams = literal('FAMILIES')
if fams:
    with open(os.path.join(RES, 'families.txt'), 'w', encoding='utf-8') as f:
        for name, words in fams.items():
            f.write(f'{name}\t{" ".join(sorted(words))}\n')

hom = literal('HOMON')
if hom:
    with open(os.path.join(RES, 'homon.txt'), 'w', encoding='utf-8') as f:
        for word, meanings in hom.items():
            parts = [f'{label}:{" ".join(sorted(ws))}' for label, ws in meanings]
            f.write(f'{word}\t{" | ".join(parts)}\n')

idioms = literal('IDIOMS')
if idioms:
    with open(os.path.join(RES, 'idioms.txt'), 'w', encoding='utf-8') as f:
        for pat, meaning in idioms:
            f.write(f'{pat}\t{meaning}\n')

# تضادها: رشتهٔ _ANT و فهرست PARADOX
pairs = set()
m = re.search(r'_ANT = """(.*?)"""', src, re.S)
if m:
    for line in m.group(1).split('\n'):
        for chunk in line.split('|'):
            parts = chunk.split()
            if len(parts) == 2:
                pairs.add(tuple(sorted(parts)))
paradox = literal('PARADOX')
if paradox:
    for item in paradox:
        if isinstance(item, (list, tuple)):
            for chunk in item:
                parts = str(chunk).split()
                if len(parts) == 2:
                    pairs.add(tuple(sorted(parts)))
if pairs:
    with open(os.path.join(RES, 'antonyms.txt'), 'w', encoding='utf-8') as f:
        for a, b in sorted(pairs):
            f.write(f'{a}\t{b}\n')
print('نوشته شد:', sorted(os.listdir(RES)))
