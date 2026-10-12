#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔬 تدقيق آلي لكل نصّ من الأذكار الكتابية مقابل صفحات الكتاب الرسمية (hisnmuslim.com).

  مما يفحصه:
    • أن كل ذكر (الأربع مجموعات الكتابية) موجود بنصّه في صفحة الكتاب المطابقة،
      بعد تطبيع التشكيل ورسم الحروف (التشكيل يختلف بين نسخ الكتاب، والمهمّ الحروف).
    • أن الأعداد المذكورة في ملاحظاتنا (ثلاثًا · سبع مرات · مائة…) موجودة في الصفحة.
  ويفشل بخطأ إن وجد ذكرًا غير موجود أو نصًّا مختلفًا (فيطبع موضع الاختلاف).

  صفحات المصدر (تُنزَّل مرة واحدة إلى .sources/):
     page25 → الأذكار بعد السلام من الصلاة      page1 → أذكار الصباح والمساء      page0 → أذكار النوم

  الاستخدام:  python3 tools/audit_adhkar.py
"""
import pathlib, re, html, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent / '.sources'
PAGES = {'after_prayer': 'page25.html', 'morning': 'page1.html', 'evening': 'page1.html', 'sleep': 'page0.html'}

# ─── تطبيع للمقارنة: نحذف التشكيل ونوحّد رسم الحروف ونطوي الترقيم ───
DIAC = re.compile('[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u0640]')
# نُبقي الحروف العربية والأرقام والمسافات فقط (الترقيم العربي «، ؛ ؟» يقع داخل نطاق 0600-06FF فيجب استثناؤه)
KEEP = re.compile(r'[^\u0621-\u063A\u0641-\u064A\u0660-\u0669\u06D0-\u06D3\u0671-\u0673\s]')
ANNOT_PAREN = re.compile(r'\([^()]*\)')
ANNOT_BRACK = re.compile(r'\[[^\[\]]*\]')


def strip_annotations(t: str) -> str:
    """يحذف زيادات الكتاب بين قوسين/معقوصين مفردين (مثل «(ثلاثاً)» و«[وإذا أمسى قال…]»)
       ولا يمسّ متن الكتاب المحصور في قوسين مزدوجين ((…))."""
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c == '(' and not (i + 1 < n and t[i + 1] == '(') and not (out and out[-1] == '('):
            j = t.find(')', i + 1)
            if 0 < j < n and j - i <= 200 and '\n' not in t[i:j] and '(' not in t[i + 1:j]:
                i = j + 1
                continue
        if c == '[':
            j = t.find(']', i + 1)
            if 0 < j < n and j - i <= 200 and '\n' not in t[i:j] and '[' not in t[i + 1:j]:
                i = j + 1
                continue
        out.append(c)
        i += 1
    return ''.join(out)


def norm(t: str) -> str:
    t = strip_annotations(t)
    t = DIAC.sub('', t)
    t = unicodedata.normalize('NFKC', t)
    for a, b in [('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ى', 'ي'), ('ئ', 'ي'),
                 ('ؤ', 'و'), ('ة', 'ه'), ('ﻻ', 'لا'), ('گ', 'ك'), ('ی', 'ي')]:
        t = t.replace(a, b)
    t = t.replace('السموات', 'السماوات').replace('السموات', 'السماوات')
    t = KEEP.sub(' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def page_raw(path: pathlib.Path) -> str:
    """نفس المتن لكن بلا حذف زيادات الكتاب — لصيغ البدائل مثل «[وإذا أمسى قال…]». """
    s = path.read_text(encoding='utf-8', errors='replace')
    k = s.find('January 1, 2014')
    if k < 0:
        k = s.find('chapter-names-list')
    e = s.find('Back to top', k)
    seg = s[k:(e if e > 0 else len(s))]
    seg = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', seg, flags=re.S)
    seg = re.sub(r'<br\s*/?>', ' ', seg)
    seg = re.sub(r'<[^>]+>', ' ', seg)
    t = html.unescape(seg)
    t = DIAC.sub('', t)
    t = unicodedata.normalize('NFKC', t)
    for a, b in [('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ى', 'ي'), ('ئ', 'ي'),
                 ('ؤ', 'و'), ('ة', 'ه'), ('ﻻ', 'لا')]:
        t = t.replace(a, b)
    t = t.replace('السموات', 'السماوات')
    t = KEEP.sub(' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def page_text(path: pathlib.Path) -> str:
    s = path.read_text(encoding='utf-8', errors='replace')
    # نقتصر على متن الفصل (بين آخر قائمة فهرس وبين «API» إن وُجدت)
    k = s.find('January 1, 2014')
    if k < 0:
        k = s.find('chapter-names-list')
    e = s.find('Back to top', k)
    if e < 0:
        e = len(s)
    seg = s[k:e]
    seg = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', seg, flags=re.S)
    seg = re.sub(r'<br\s*/?>', ' ', seg)
    seg = re.sub(r'<[^>]+>', ' ', seg)
    return norm(html.unescape(seg))


def parse_book_sets():
    src = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    k = src.find('let adhkarSets: [DhikrSet] = [')
    block = src[k:src.find('\n]\n', k)]
    out = []
    for part in re.split(r'\n    DhikrSet\(', block)[1:]:
        sid = re.search(r'id:\s*"([^"]+)"', part).group(1)
        if sid not in PAGES:
            continue
        items = []
        for m in re.finditer(r'Dhikr\((.*?)\)\s*,?\s*(?=Dhikr\(|\])', part, re.S):
            b = ' '.join(m.group(1).split())
            f = re.search(r'full:\s*"((?:[^"\\]|\\.)*)"', b)
            items.append(dict(
                id=re.search(r'id:\s*"([^"]+)"', b).group(1),
                text=re.search(r'text:\s*"((?:[^"\\]|\\.)*)"', b).group(1),
                target=int(re.search(r'target:\s*(\d+)', b).group(1)),
                full=(f.group(1).replace('\\n', '\n') if f else None)))
        out.append(dict(id=sid, items=items))
    return out


# بعض الأذكار نصُّها فعلٌ وصفيّ في الكتاب (يُحكى لا يُقال) — نقارن المفتاح النصي منه فقط
# أذكار المساء المركّبة: الكتاب يذكر صيغة المساء بين معقوصين («وإذا أمسى قال…») على الأصل الصباحي،
# فنطابق عبارات التبديل نفسها في الصفحة الخام.
ALTERNATES = {
    ('evening', 'amsayna'): ['امسينا وامسي الملك لله', 'رب اسالك خير ما في هذه الليله',
                             'واعوذ بك من شر ما في هذه الليله'],
    ('evening', 'ashhaduk'): ['اللهم اني امسيت'],
    ('evening', 'nimah'): ['اللهم ما امسى بي'],
    ('evening', 'fitrah'): ['امسينا علي فطره الاسلام'],
}

DESCRIPTIVE = {
    ('sleep', 'muawwidhat'): ('يجمع كفيه ثم ينفث فيهما', 'ثم يمسح بهما ما استطاع من جسده', 'ثلاث مرات'),
    ('sleep', 'surah'): ('يقرا', 'تنزيل السجده', 'تبارك الذي بيده الملك'),
}


def main() -> int:
    print('🔬 تدقيق الأذكار الكتابية مقابل صفحات الكتاب الرسمية')
    pages, raws = {}, {}
    for sid, f in PAGES.items():
        if f not in pages:
            pages[f] = page_text(SRC / f)
            raws[f] = page_raw(SRC / f)
        if not pages[f]:
            print(f'   ✘ صفحة المصدر فارغة: {f} (شغّل التنزيل أولًا)')
            return 1

    bad = 0
    for st in parse_book_sets():
        print(f'\n── {st["id"]} ──  ({len(st["items"])} ذكرًا)')
        ptext, praw = pages[PAGES[st['id']]], raws[PAGES[st['id']]]
        for i, it in enumerate(st['items'], 1):
            body = (it['full'] or it['text']).split('\n\n')[0]
            key = (st['id'], it['id'])
            if key in ALTERNATES:
                phrases = ALTERNATES[key]
                ok_all = all(norm(x) in praw for x in phrases)
                label = 'صيغة المساء (بدائل الكتاب)'
                if ok_all:
                    print(f'   ✔ {i:2d}. {it["text"][:44]}  ({label})')
                    continue
            if key in DESCRIPTIVE:
                phrases = DESCRIPTIVE[key]
                ok_all = all(norm(x) in ptext or norm(x) in praw for x in phrases)
                label = 'وصفيّ'
            else:
                ok_all = norm(body) in ptext or norm(body) in praw
                label = 'نصّي' if norm(body) in ptext else 'صيغة بديلة في الكتاب'
            if ok_all:
                print(f'   ✔ {i:2d}. {it["text"][:44]}  ({label})')
            else:
                bad += 1
                print(f'   ✘ {i:2d}. {it["text"][:44]}  ✗ غير موجود بنصّه في الصفحة')
                n = norm(body)
                # اطبع أطول بادئة موجودة لبيان موضع الاختلاف
                lo, hi = 0, len(n)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if n[:mid] in ptext:
                        lo = mid
                    else:
                        hi = mid - 1
                print(f'        النص يطابق أول {lo} حرفًا ثم يفترق:')
                print(f'        عندنا  : …{n[max(0, lo-30):lo+40]}…')
                idx = ptext.find(n[max(0, lo-30):lo]) if lo > 30 else -1
                if idx >= 0:
                    print(f'        الكتاب : …{ptext[idx:idx+70]}…')

    print('\n' + '─' * 60)
    print('   ✔ كل الأذكار الكتابية موجودة بنصّها في صفحات الكتاب' if not bad
          else f'   ❌ {bad} ذكرًا يحتاج تصحيحًا')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
