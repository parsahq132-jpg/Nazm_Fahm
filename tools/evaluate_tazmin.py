#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ارزیابی تشخیص تضمین روی مجموعهٔ آزمونِ دست‌برچسب (corpus/tazmin_probe.jsonl).

این مجموعه برچسبِ انسانیِ مستقل ندارد و برچسب‌های آن را نویسندهٔ همین ابزار
بر پایهٔ تعریف تضمین گذاشته است؛ پس نتیجه، سنجشِ درستیِ «قاعده» است، نه
دقتِ میدانی روی پیکرهٔ آزاد. نمونه‌ها از شعر کلاسیک و معاصر انتخاب شده‌اند.

خروجی: Precision / Recall / F1 و فهرست خطاها، به فارسی.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(HERE, 'corpus', 'tazmin_probe.jsonl')
FINAL = os.path.join(HERE, 'TheORIGINAL_FINAL.py')


def load_module(path):
    spec = importlib.util.spec_from_file_location('engine', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def metrics(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 1)
    fp = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(ys, ps) if y == 1 and p == 0)
    tn = sum(1 for y, p in zip(ys, ps) if y == 0 and p == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(ys) if ys else 0.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=prec, recall=rec, f1=f1, accuracy=acc)


def predict(mod, text, confirmed_only=True):
    res = mod.analyze(text.replace(' / ', '\t'))
    hits = [f for f in res.findings if f.device == 'تضمین' and f.status != 'رد']
    if confirmed_only:
        hits = [f for f in hits if f.status == 'تأیید']
    return hits


def main():
    mod = load_module(FINAL)
    mod.load_external_resources()

    rows = [json.loads(line) for line in open(PROBE, encoding='utf-8') if line.strip()]
    ys = [r['label'] for r in rows]
    out = {}
    print(f'\n== مجموعهٔ آزمون تضمین: {len(rows)} مورد '
          f'(مثبت={sum(ys)}، منفی={len(ys) - sum(ys)}) ==\n')

    for name, confirmed in (('تضمین — فقط تأییدشده', True),
                            ('تضمین — با احتیاط هم پذیرفته', False)):
        ps = [1 if predict(mod, r['text'], confirmed) else 0 for r in rows]
        m = metrics(ys, ps)
        out[name] = m
        print(f"{name:<28} P={m['precision']*100:5.1f}٪  R={m['recall']*100:5.1f}٪  "
              f"F1={m['f1']*100:5.1f}٪  Acc={m['accuracy']*100:5.1f}٪  "
              f"(TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']})")

    print('\n— خطاها —')
    for r in rows:
        hits = predict(mod, r['text'], confirmed_only=True)
        pred = 1 if hits else 0
        if pred == r['label']:
            continue
        kind = 'مثبت کاذب' if pred == 1 else 'منفی کاذب'
        ev = '؛ '.join(f'«{h.evidence}» → {h.note}' for h in hits) or '—'
        print(f'  [{kind}] {r["text"]}\n     شاهد: {ev}\n     توضیح: {r["note"]}')

    os.makedirs(os.path.join(HERE, 'reports'), exist_ok=True)
    path = os.path.join(HERE, 'reports', 'metrics_tazmin.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\nنتیجه ذخیره شد: {path}')


if __name__ == '__main__':
    main()
