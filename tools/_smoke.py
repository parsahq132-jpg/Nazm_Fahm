# -*- coding: utf-8 -*-
"""آزمون دود: مسیر کامل تحلیل و تولید گزارش که رابط کاربری استفاده می‌کند."""
import importlib.util

spec = importlib.util.spec_from_file_location('e', 'TheORIGINAL_FINAL.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.load_external_resources()

text = (
    "دلم چو کبوتری در قفس می‌طپد\tقدش چو سروِ سهی می‌خرامد\n"
    "ابر گریست و باغ خندید\tگل از شادیِ باران شکفت\n"
    "به قولِ حافظ: یوسف گم‌گشته بازآید به کنعان غم مخور\tکه این بشارتِ دل‌های خسته است\n"
    "چه سود از عمری که در غفلت گذشت؟\tکه یک نفس به هوش نیامدیم\n"
    "تو روشن و من تاریک\tمن تاریک و تو روشن\n"
    "ندانم این که می‌بینم چه کسی است؟\tکه دل از دیدنش آشفته شد"
)
res = m.analyze(text, progress=lambda p, s: None)
print('beits', len(res.beits), 'findings', len(res.findings))
devices = sorted({f.device for f in res.findings})
print('devices', devices)
assert 'تضمین' in devices and 'استفهام انکاری' in devices and 'عکس' in devices
rows = m.table_rows(res)
print('table rows', len(rows))
for f in res.findings:
    steps = m.six_steps(f)
    assert len(steps) == 6
print('six_steps ok')
s6 = m.txt_step6(res)
s7 = m.txt_step7(res)
assert 'زیرگونه‌های جناس' in s6 and 'سیاست سکوت' in s6
assert 'گزارش نهایی' in s7
print('reports chars', len(s6), len(s7))
print('OK')
