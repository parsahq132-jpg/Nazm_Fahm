#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ارزیابی بیرونی موتور تشخیص تلمیح روی پیکرهٔ برچسب‌خوردهٔ گنجور.

برچسب‌ها از برچسب‌های تأییدشدهٔ انسانی گنجور می‌آیند:
  Allusion    → تلمیح دارد (مثبت)
  Participant → نام در بیت هست ولی شخصیت بخشی از روایت است، نه تلمیح (منفی سخت)

دو سامانه اندازه‌گیری می‌شود:
  1) خط پایه: منطق نسخهٔ اولیه — تطبیق سادهٔ نام/عبارت (هر واژه از فهرست تلمیح).
  2) نسخهٔ نهایی: تشخیص شاهد‌محور فایل TheORIGINAL_FINAL.py.

معیارها: Precision، Recall، F1، FPR، Accuracy.
مجموعهٔ آزمون در هیچ مرحله‌ای برای تنظیم قواعد استفاده نشده است (تنظیم روی val).
"""
import argparse
import collections
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(HERE, 'corpus', 'ganjoor_labeled.jsonl')
FINAL = os.path.join(HERE, 'TheORIGINAL_FINAL.py')


def load_module(path):
    spec = importlib.util.spec_from_file_location('engine', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows(split):
    out = []
    with open(CORPUS, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if r['split'] != split:
                continue
            # برچسب‌های حدسی (ابیات بدون برچسب گنجور) در آزمون حساب نمی‌شوند
            if r['label_source'] != 'ganjoor_approved_person_tag':
                continue
            out.append(r)
    return out


def metrics(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 0)
    tn = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    acc = (tp + tn) / len(ys) if ys else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn, 'precision': prec,
            'recall': rec, 'f1': f1, 'fpr': fpr, 'accuracy': acc}


def fmt(name, m):
    return (f"{name:<12} P={m['precision']*100:5.1f}٪  R={m['recall']*100:5.1f}٪  "
            f"F1={m['f1']*100:5.1f}٪  FPR={m['fpr']*100:5.1f}٪  "
            f"Acc={m['accuracy']*100:5.1f}٪  "
            f"(TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']})")


def baseline_detector(mod):
    """منطق نسخهٔ اولیه: هر واژه/عبارت موجود در فهرست تلمیح = تلمیح."""
    idx = mod._talmih_index()
    keys = sorted(idx, key=len, reverse=True)

    def predict(text):
        toks = mod.WORD_RE.findall(mod.normalize(text.replace(' / ', ' ')))
        joined = ''.join(toks)
        for k in keys:
            if len(k) == 1:
                continue
            if k in joined:
                return 1
        return 0

    return predict


def final_detector(mod, confirmed_only=True):
    def predict(text):
        res = mod.analyze(text.replace(' / ', '\t'))
        for f in res.findings:
            if f.device != 'تلمیح':
                continue
            if confirmed_only and f.status != 'تأیید':
                continue
            if not confirmed_only and f.status == 'رد':
                continue
            return 1
        return 0

    return predict


def run(split, only=None):
    data = rows(split)
    ys = [r['label'] for r in data]
    print(f'\n== {split}: {len(data)} بیت (مثبت={sum(ys)}، منفی={len(ys)-sum(ys)}) ==')
    results = {}

    mod = load_module(FINAL)
    mod.load_external_resources()

    for name, pred in (
        ('baseline', baseline_detector(mod)),
        ('final', final_detector(mod, confirmed_only=True)),
        ('final-lenient', final_detector(mod, confirmed_only=False)),
    ):
        if only and name not in only:
            continue
        t0 = time.time()
        ps = [pred(r['text']) for r in data]
        dt = time.time() - t0
        m = metrics(ys, ps)
        m['seconds'] = dt
        results[name] = m
        print(fmt(name, m) + f'  [{dt:.1f}s]')
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--split', default='test', choices=['train', 'val', 'test', 'all'])
    args = ap.parse_args()
    splits = ['val', 'test'] if args.split == 'all' else [args.split]
    out = {s: run(s) for s in splits}
    os.makedirs(os.path.join(HERE, 'reports'), exist_ok=True)
    path = os.path.join(HERE, 'reports', f'metrics_{args.split}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\nنتیجه ذخیره شد: {path}')


if __name__ == '__main__':
    main()
