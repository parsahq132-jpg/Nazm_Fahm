#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سنجش جداگانهٔ دقت هر آرایه روی مجموعهٔ طلاییِ دست‌برچسب.

هر سطر `corpus/devices_gold.jsonl` یک قطعه متن و مجموعهٔ آرایه‌های موجود در آن است.
برای هر آرایه:
  مثبت‌ها = قطعه‌هایی که آن آرایه در gold هست
  منفی‌ها = بقیهٔ قطعه‌ها
تشخیص «پذیرفته» آن است که آرایه با وضعیت «تأیید» گزارش شود (حالت سخت‌گیرانه).
حالت دوم (با «با احتیاط») هم برای شفافیت گزارش می‌شود.

اجرا:
  python tools/evaluate_devices.py                 # گزارش جدولی
  python tools/evaluate_devices.py --json reports/devices_now.json
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL = os.path.join(HERE, 'TheORIGINAL_FINAL.py')
GOLD = os.path.join(HERE, 'corpus', 'devices_gold.jsonl')

# آرایه‌های ساختاری (قافیه/ردیف/روی/تصریع) به کل شعر نیاز دارند و در این
# مجموعهٔ تک‌بیتی سنجیده نمی‌شوند.
FORM_LEVEL = ('قافیه', 'ردیف', 'روی', 'تصریع')


def load_module(path=None):
    spec = importlib.util.spec_from_file_location('engine', path or FINAL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.load_external_resources()
    return mod


def load_gold():
    items = []
    with open(GOLD, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def predicted(res, strict=True):
    """آرایه‌های گزارش‌شده. استعارهٔ مکنیه هم استعاره است و هم تشخیص."""
    out = set()
    for f in res.findings:
        if f.device in FORM_LEVEL:
            continue
        if strict and f.status != 'تأیید':
            continue
        if f.status == 'رد':
            continue
        out.add(f.device)
        if f.device == 'موازنه':
            out.add('سجع')      # موازنه زیرگونهٔ سجع است
    return out


def metrics(n, tp, fp, fn, tn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {'precision': p, 'recall': r, 'f1': f1, 'accuracy': (tp + tn) / n if n else 0.0,
            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}


def run(json_out=None, engine=None):
    mod = load_module(engine)
    items = load_gold()
    devices = [d for d in mod.META if d not in FORM_LEVEL]

    preds = {}
    for it in items:
        res = mod.analyze(it['text'])
        preds[it['id']] = (predicted(res, True), predicted(res, False))

    report = {'n_items': len(items), 'devices': {}}
    for dev in devices:
        tp = fp = fn = tn = 0
        fps, fns = [], []
        for it in items:
            gold = dev in it['gold']
            pred = dev in preds[it['id']][0]
            if gold and pred:
                tp += 1
            elif gold and not pred:
                fn += 1
                fns.append(it['id'])
            elif pred and not gold:
                fp += 1
                fps.append({'id': it['id'], 'text': it['text'].replace('\t', ' / '),
                            'gold': it['gold']})
            else:
                tn += 1
        m = metrics(len(items), tp, fp, fn, tn)
        lenient_tp = sum(1 for it in items
                         if dev in it['gold'] and dev in preds[it['id']][1])
        m['lenient_recall'] = lenient_tp / (lenient_tp + fn) if (lenient_tp + fn) else 0.0
        m['fp_examples'] = fps[:4]
        m['fn_examples'] = fns[:4]
        report['devices'][dev] = m

    if json_out:
        os.makedirs(os.path.dirname(os.path.join(HERE, json_out)) or '.', exist_ok=True)
        with open(os.path.join(HERE, json_out), 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n== سنجش آرایه‌به‌آرایه: {len(items)} قطعهٔ دست‌برچسب ==\n")
    print(f"{'آرایه':<16}{'P٪':>7}{'R٪':>7}{'F1٪':>7}{'Acc٪':>7}"
          f"{'TP':>4}{'FP':>4}{'FN':>4}{'TN':>4}  {'با احتیاط R٪':>12}")
    for dev in devices:
        m = report['devices'][dev]
        print(f"{dev:<16}{m['precision']*100:7.1f}{m['recall']*100:7.1f}"
              f"{m['f1']*100:7.1f}{m['accuracy']*100:7.1f}"
              f"{m['tp']:4d}{m['fp']:4d}{m['fn']:4d}{m['tn']:4d}"
              f"{m['lenient_recall']*100:12.1f}")

    print('\n── نمونهٔ مثبت‌های کاذب ──')
    for dev in devices:
        m = report['devices'][dev]
        if m['fp_examples']:
            print(f"\n{dev}:")
            for e in m['fp_examples']:
                print(f"  ✗ {e['id']}: {e['text'][:70]}  [gold={e['gold']}]")

    print('\n── نمونهٔ منفی‌های کاذب ──')
    for dev in devices:
        m = report['devices'][dev]
        if m['fn_examples']:
            print(f"  {dev}: {', '.join(m['fn_examples'])}")
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default='')
    ap.add_argument('--engine', default='')
    args = ap.parse_args()
    run(args.json or None, args.engine or None)
