#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ساخت پایگاه تلمیح (resources/talmih.txt) و فرادادهٔ آن (resources/talmih_meta.txt).

منابع:
1) people.json از دادهٔ عمومی گنجور — ۶۶۲ شخصیت با توضیح تأییدشده/مستند
2) فهرست تلمیح‌های نسخهٔ اولیهٔ برنامه (لیست داخلی TALMIH)
3) عبارت‌های Episodeای دست‌نویس (resources_src/episodes.tsv)

قالب خروجی talmih.txt دقیقاً:  عبارت<TAB>توضیح
فراداده (نوع و نشانه‌های بافتی) در فایل جدا می‌ماند تا قالب اصلی دست‌نخورده بماند.
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(HERE, 'resources')
SRC = os.path.join(HERE, 'resources_src')

STOP_DESC = set('''اشاره داستان داستانی مربوط مرتبط شخصیت نام پسر دختر پدر مادر برادر خواهر
پادشاه شاه prince princess از به در با که و یا این آن است بود شده می‌شود دارد دارد.
اسطوره‌ای تاریخی ایرانی فارسی‌زبان شاعر نویسنده یکی دیگر نیز هم بر'''.split())

# توضیح شخصیت‌هایی که در people.json توضیح ندارند
FILL = {
    'کیومرث': 'نخستین پادشاه پیشدادی و آغاز آفرینش شاهنامه',
    'سیامک': 'پسر کیومرث که به دست دیو سپید کشته شد',
    'خروزان دیو': 'دیوی که سیامک را کشت و به دست هوشنگ کشته شد',
    'هوشنگ': 'پادشاه پیشدادی، آتش‌یاب و بنیان‌گذار جشن سده',
    'طهمورث': 'پادشاه پیشدادی که دیوان را به بند کشید',
    'جمشید': 'پادشاه اساطیری که جام جهان‌نما و تخت جمشید از اوست و به دست ضحاک کشته شد',
    'مرداس': 'پدر ضحاک، پادشاه عرب',
    'ضحاک': 'پادشاه ستمگر ماردوش که با داستان فریدون و کاوه آهنگر ارتباط دارد',
    'شهرناز': 'دختر جمشید و همسر ضحاک',
    'ارنواز': 'دختر جمشید و همسر ضحاک',
    'اهریمن': 'دشمن اصلی جهان در اساطیر ایران و منشأ بدی',
    'سروش': 'فرشتهٔ پیام‌رسان در اساطیر ایران',
    'شهرسپ': 'از پهلوانان دربار ضحاک',
    'دیو سیاه': 'دیوی که در داستان سیامک و هوشنگ نقش دارد',
    'ابلیس': 'شیطان، دشمن آدم و منشأ وسوسه',
    'ارمایل': 'آشپز ضحاک و نجات‌دهندهٔ جوانان از مارهای دوش او',
    'فارک': 'از همراهان ارمایل در آشپزی ضحاک',
    'نونک': 'از اسیران آشپزخانهٔ ضحاک',
    'مهارو': 'از اسیران آشپزخانهٔ ضحاک',
    'آبتین': 'پدر فریدون که به دست ضحاک کشته شد',
    'فرانک': 'مادر فریدون که او را از ضحاک پنهان کرد',
    'فریدون': 'پهلوان اساطیری که ضحاک را در دماوند به بند کشید',
    'گاو برمایه': 'گاوی که فریدون را شیر داد',
    'کاوه': 'کاوهٔ آهنگر، قیام‌کننده علیه ضحاک و برافرازندهٔ درفش کاویانی',
    'کیانوش': 'از نیاکان کاوه آهنگر',
    'پرمایه': 'از پسران کاوه آهنگر',
    'کندرو': 'از پسران کاوه آهنگر',
    'جندل': 'از یاران کاوه در قیام علیه ضحاک',
    'ایرج': 'پسر کوچک فریدون که به دست برادرانش تور و سلم کشته شد',
    'سلم': 'پسر فریدون و از قاتلان ایرج',
    'تور': 'پسر فریدون و از قاتلان ایرج',
    'ماه‌آفرید': 'همسر ایرج',
    'پشنگ': 'پدر افراسیاب، پادشاه توران',
    'منوچهر': 'پادشاه پیشدادی که انتقام ایرج را گرفت',
    'سهی': 'از یاران منوچهر',
    'آرزو': 'دختر سهی در داستان سیاوش',
    'آزاده': 'کنیز و همراه بهرام گور در شکار',
    'قارن کاوگان': 'پهلوان ایرانی و از یاران کاوه و فریدون',
    'شیروی': 'از پهلوانان ایرانی در داستان سیاوش',
    'آوگان': 'از پهلوانان ایرانی',
    'شاپور': 'پادشاه ساسانی و نیز نام چند پهلوان ایرانی',
    'نستوه': 'از پهلوانان ایرانی در شاهنامه',
    'شیدوش': 'از پهلوانان ایرانی در شاهنامه',
    'سام': 'پهلوان ایرانی، پدر زال و نیای رستم',
    'قباد': 'از پادشاهان کیانی و پدر کیکاوس',
    'گرد تلیمان نژاد': 'از پهلوانان تورانی در شاهنامه',
    'سیمرغ': 'پرندهٔ اساطیری که زال و رستم را پرورد',
    'نوذر': 'پادشاه پیشدادی که در نبرد با تورانیان کشته شد',
    'مهراب': 'پادشاه کابل و پدر رودابه',
    'سیندخت': 'همسر مهراب و مادر رودابه',
    'کاکوی': 'از پهلوانان در داستان زال و رودابه',
    'رستم': 'پهلوان بزرگ ایران، کشندهٔ دیو سفید و سهراب',
    'افراسیاب': 'پادشاه توران و دشمن ایران در شاهنامه',
    'زادْشم': 'پهلوان تورانی و از یاران افراسیاب',
    'ویسه': 'وزیر و خویشاوند افراسیاب',
    'ارجسپ': 'پادشاه توران و از دشمنان ایرانیان',
    'گرسیوز': 'برادر افراسیاب و عامل قتل سیاوش',
    'بارمان': 'پهلوان تورانی در نبرد با ایرانیان',
    'کلباد': 'پهلوان تورانی در شاهنامه',
    'اغریرث': 'برادر افراسیاب که به ایرانیان پیوست',
    'شماساس': 'از پهلوانان تورانی',
    'خزروان': 'از پهلوانان تورانی',
    'طوس': 'پهلوان ایرانی و فرماندهٔ سپاه کیخسرو',
    'گستهم': 'پهلوان ایرانی و برادر طوس',
    'کروخان': 'از پهلوانان تورانی',
    'گژدهم': 'پهلوان ایرانی در داستان سیاوش',
    'برزین': 'از پهلوانان ایرانی',
    'خراد': 'از پهلوانان ایرانی',
    'طهماسب': 'از پهلوانان ایرانی در شاهنامه',
    'زو': 'پادشاه پیشدادی پس از نوذر',
    'گرشاسپ': 'پهلوان اساطیری که اژدها را کشت',
    'کیقباد': 'نخستین پادشاه کیانی',
    'قلون': 'از پهلوانان در داستان کیقباد',
    'کی‌پشین': 'یکی از پادشاهان کیانی در روایات',
    'آرش پسر کیقباد': 'از شاهزادگان کیانی',
    'کی‌آرش': 'از پادشاهان کیانی در روایات',
    'بسوتام': 'از پهلوانان ایرانی',
    'طلخند': 'از پهلوانان ایرانی',
    'قوام‌الدین حسن شیرازی': 'درگذشتهٔ ۷۴۲ ق، شاعر و دبیر ایرانی',
    'سعدی': 'شاعر بزرگ شیراز، سرایندهٔ گلستان و بوستان',
    'امامی هروی': 'شاعر پارسی‌گوی سدهٔ هفتم در هرات',
}

TYPE_RULES = [
    ('quran', 'قرآن پیامبر امام آیه سوره وحی بهشت دوزخ قیامت فرشته شیطان'),
    ('shahnameh', 'شاهنامه پهلوان ضحاک کیانی توران افراسیاب رستم سیاوش کیومرث'),
    ('history', 'تاریخ سلسله خلیفه جنگ نبرد شهر بغداد قادسیه پادشاه'),
    ('religion', 'امام شیعه عاشورا کربلا حدیث زیارت مهدی علی حسین'),
    ('literature', 'شاعر مثنوی غزل دیوان اثر سراینده'),
]


def norm_space(s):
    s = s.replace('\u200c', ' ').replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def clean_desc(s, limit=170):
    s = norm_space(str(s)).strip(' .،؛')
    if len(s) > limit:
        cut = s[:limit]
        idx = max(cut.rfind('،'), cut.rfind(';'), cut.rfind('.'))
        s = cut[:idx] if idx > 60 else cut
    s = s.rstrip(' .،؛')
    if s and s[-1] not in '.)»':
        s += '.'
    return s


def infer_type(text):
    for t, keys in TYPE_RULES:
        if any(k in text for k in keys.split()):
            return t
    return 'person'


def cues_from_desc(desc):
    words = re.findall(r'[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]{3,}', desc)
    out = []
    for w in words:
        if w in STOP_DESC or w in out:
            continue
        out.append(w)
        if len(out) >= 6:
            break
    return out


def load_episodes():
    items = []
    for fname in ('episodes.tsv', 'supplement.tsv'):
        items.extend(_load_tsv(os.path.join(SRC, fname)))
    return items


def _load_tsv(path):
    items = []
    if not os.path.exists(path):
        return items
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        phrase = norm_space(parts[0])
        desc = clean_desc(parts[1])
        cues = [c for c in re.split(r'[ ،,|]+', parts[2]) if c] if len(parts) > 2 else []
        typ = infer_type(desc + ' ' + phrase)
        if phrase and desc:
            items.append((phrase, desc, cues, typ))
    return items


def main():
    os.makedirs(RES, exist_ok=True)
    people = json.load(open(os.path.join(HERE, 'ganjoor_raw', 'people.json'), encoding='utf-8'))
    original = json.load(open(os.path.join(HERE, 'ganjoor_raw', 'original_talmih.json'), encoding='utf-8'))

    entries = {}

    def add(phrase, desc, cues, typ, source):
        phrase = norm_space(phrase)
        if not phrase or len(phrase) < 2:
            return
        key = phrase.replace(' ', '')
        if key in entries:
            # توضیح طولانی‌تر/بهتر را نگه می‌داریم
            if len(desc) > len(entries[key]['desc']) + 20:
                entries[key]['desc'] = desc
            entries[key]['cues'] = sorted(set(entries[key]['cues']) | set(cues))
            return
        entries[key] = {'phrase': phrase, 'desc': desc, 'cues': list(dict.fromkeys(cues)),
                        'type': typ, 'source': source}

    for p in people:
        name = norm_space(p['Name'])
        desc = p.get('Description') or FILL.get(name)
        if not desc:
            print(f'  ! بی‌توضیح: {name}', file=sys.stderr)
            continue
        desc = clean_desc(desc)
        typ = infer_type(desc)
        cues = cues_from_desc(desc)
        add(name, desc, cues, typ, 'ganjoor_people')
        aliases = p.get('Aliases') or ''
        for al in re.split(r'[،,؛/]+', aliases):
            al = norm_space(al)
            if al and al != name and len(al) >= 3:
                add(al, desc, cues, typ, 'ganjoor_people')

    for term, note, partners in original:
        desc = clean_desc(note)
        # نشانه‌ها ممکن است رشته باشند؛ iterate کردنِ رشته حروف را جدا می‌کرد
        # و فرادادهٔ بی‌فایده («م|ی|ه|ن») می‌ساخت.
        if isinstance(partners, str):
            partners = re.split(r'[ ،,|]+', partners)
        cues = [c for c in (partners or []) if c]
        add(term, desc, cues, infer_type(note + ' ' + term), 'original_list')

    ep = load_episodes()
    for phrase, desc, cues, typ in ep:
        add(phrase, desc, cues, typ, 'curated_episode')

    ordered = sorted(entries.values(), key=lambda e: (-len(e['phrase']), e['phrase']))
    tal = os.path.join(RES, 'talmih.txt')
    meta = os.path.join(RES, 'talmih_meta.txt')
    with open(tal, 'w', encoding='utf-8') as f:
        for e in ordered:
            f.write(f"{e['phrase']}\t{e['desc']}\n")
    with open(meta, 'w', encoding='utf-8') as f:
        for e in ordered:
            cues = '|'.join(c for c in e['cues'] if c not in STOP_DESC)
            f.write(f"{e['phrase']}\t{e['type']}\t{cues}\n")

    src = Counter(e['source'] for e in ordered)
    typ = Counter(e['type'] for e in ordered)
    print(f'تلمیح‌های نوشته‌شده: {len(ordered)}  → {tal}')
    print('  بر اساس منبع:', dict(src))
    print('  بر اساس نوع:', dict(typ))
    print(f'  مدخل‌های دارای نشانهٔ بافتی: {sum(1 for e in ordered if e["cues"])}')


if __name__ == '__main__':
    main()
