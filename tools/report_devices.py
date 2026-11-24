# -*- coding: utf-8 -*-
"""ساخت جدول مقایسهٔ قبل/بعد از دو فایل JSON سنجش آرایه‌ها."""
import json
import sys


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


base = load('reports/devices_baseline.json')
after = load('reports/devices_after.json')
fa = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
pct = lambda x: f'{x * 100:.0f}'.translate(fa)

order = list(after['devices'])
rows = []
for d in order:
    b = base['devices'].get(d, {})
    a = after['devices'][d]
    rows.append((d, b, a))

lines = []
lines.append('| آرایه | P پیش | R پیش | F1 پیش | Acc پیش | P پس | R پس | F1 پس | Acc پس | TP/FP/FN پس |')
lines.append('|---|---|---|---|---|---|---|---|---|---|')
for d, b, a in rows:
    lines.append(
        f"| {d} | {pct(b.get('precision', 0))}٪ | {pct(b.get('recall', 0))}٪ | "
        f"{pct(b.get('f1', 0))}٪ | {pct(b.get('accuracy', 0))}٪ | "
        f"**{pct(a['precision'])}٪** | **{pct(a['recall'])}٪** | **{pct(a['f1'])}٪** | "
        f"**{pct(a['accuracy'])}٪** | {a['tp']}/{a['fp']}/{a['fn']} |")
print('\n'.join(lines))

# میانگین ماکرو فقط روی آرایه‌هایی که در gold مثبت دارند
def macro(rep):
    vals = [m for m in rep['devices'].values() if m['tp'] + m['fn'] > 0]
    return {k: sum(m[k] for m in vals) / len(vals) for k in ('precision', 'recall', 'f1', 'accuracy')}, len(vals)


mb, nb = macro(base)
ma, na = macro(after)
print(f"\nماکرو ({na} آرایه با نمونهٔ مثبت):")
print(f"  پیش:  P={pct(mb['precision'])}٪ R={pct(mb['recall'])}٪ F1={pct(mb['f1'])}٪ Acc={pct(mb['accuracy'])}٪")
print(f"  پس:   P={pct(ma['precision'])}٪ R={pct(ma['recall'])}٪ F1={pct(ma['f1'])}٪ Acc={pct(ma['accuracy'])}٪")

if len(sys.argv) > 1:
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
