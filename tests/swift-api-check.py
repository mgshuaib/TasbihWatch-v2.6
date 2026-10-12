#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 فاحص تطابق واجهات Swift ومحتوى الأذكار
سبحة — أداة تُشغَّل قبل كل تسليم (بدون Mac)

يفحص:
  ① أن كل نداء `SharedCounter.xxx()` / `SharedKeys.xxx` موجود فعلًا في Shared.swift
     (مع تجاهل التعليقات — درسٌ من خطأ `SharedCounter.increment()` المحذوفة)
  ② أن كل ملف مصدر مذكور في project.yml / project-container.yml موجود فعليًا
  ③ أن نصوص الأذكار الكاملة متطابقة بين Swift و المحاكي (عدد + المحتوى)

الاستخدام:  python3 tests/swift-api-check.py
"""

import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ok_all = True


def strip_comments(src: str) -> str:
    """يحذف تعليقات // و /* */ حتى لا نُبلّغ عن نداءات موجودة في الشرح فقط."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    out = []
    for line in src.splitlines():
        # تجاهل ما بعد // مع مراعاة عدم وجود // داخل نص عادي (تقريب كافٍ هنا)
        idx = line.find('//')
        out.append(line[:idx] if idx >= 0 else line)
    return '\n'.join(out)


def check_apis() -> bool:
    shared = strip_comments((ROOT / 'Shared.swift').read_text(encoding='utf-8'))
    funcs = set(re.findall(r'static func (\w+)', shared))
    keys = set(re.findall(r'static let (\w+)\s*=', shared))

    targets = ['Widget/IncrementIntent.swift', 'Widget/TasbihWidget.swift', 'CounterModel.swift',
               'CounterView.swift', 'ReadingView.swift', 'OptionsPanel.swift', 'MenuView.swift',
               'SetBackgrounds.swift', 'TasbihApp.swift', 'SessionManager.swift', 'Shared.swift']
    bad = []
    for f in targets:
        p = ROOT / f
        if not p.exists():
            continue
        src = strip_comments(p.read_text(encoding='utf-8'))
        for m in re.finditer(r'SharedCounter\.(\w+)\s*\(', src):
            if m.group(1) not in funcs:
                bad.append(f'{f}: SharedCounter.{m.group(1)}() غير موجودة')
        for m in re.finditer(r'SharedKeys\.(\w+)', src):
            if m.group(1) not in keys:
                bad.append(f'{f}: SharedKeys.{m.group(1)} غير موجود')

    print('① نداءات الكود المشترك')
    if bad:
        for b in bad:
            print('   ✘ ' + b)
        return False
    print(f'   ✔ {len(targets)} ملفًا · لا نداء لدالة أو مفتاح محذوف')
    return True


def check_sources() -> bool:
    print('② مصادر ملفات المشروع (yml)')
    try:
        import yaml
    except ImportError:
        print('   ⚠ PyYAML غير مثبّت — تخطّي (pip install pyyaml)')
        return True
    ok = True
    for name in ['project.yml', 'project-container.yml']:
        p = ROOT / name
        if not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        miss = []
        for _, t in (d.get('targets') or {}).items():
            for s in (t.get('sources') or []):
                path = s if isinstance(s, str) else s.get('path', '')
                if path and not (ROOT / path.rstrip('/')).exists():
                    miss.append(path)
        if miss:
            ok = False
            print(f'   ✘ {name}: مصادر مفقودة {miss}')
        else:
            print(f'   ✔ {name}: كل المصادر موجودة')
    return ok


def parse_swift_sets(sw: str):
    """مجموعات Swift: [ {id, items:[(id, text, target, full)]} ]"""
    k = sw.find('let adhkarSets: [DhikrSet] = [')
    block = sw[k:sw.find('\n]\n', k)]
    out = []
    for part in re.split(r'\n    DhikrSet\(', block)[1:]:
        sid = re.search(r'id:\s*"([^"]+)"', part).group(1)
        items = []
        for m in re.finditer(r'Dhikr\((.*?)\)\s*,?\s*(?=Dhikr\(|\])', part, re.S):
            b = ' '.join(m.group(1).split())
            f = re.search(r'full:\s*"((?:[^"\\]|\\.)*)"', b)
            items.append((re.search(r'id:\s*"([^"]+)"', b).group(1),
                          re.search(r'text:\s*"((?:[^"\\]|\\.)*)"', b).group(1),
                          int(re.search(r'target:\s*(\d+)', b).group(1)),
                          f.group(1) if f else None))
        out.append({'id': sid, 'items': items})
    return out


def parse_sim_sets(sim: str):
    """مجموعات المحاكي: [ {id, items:[(id, text, target)]} ] + قاموس FULL"""
    k = sim.find('const SETS')
    sets_block = sim[k:sim.find('const FULL', k)]
    fk = sim.find('const FULL = {')
    full = dict(re.findall(r'^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$',
                           sim[fk:sim.find('\n};', fk)], re.M))
    out = []
    for m in re.finditer(r'\{ id:"([^"]+)".*?items:\[(.*?)\]', sets_block, re.S):
        items = [(a, b, int(c)) for a, b, c in
                 re.findall(r'\{id:"([^"]+)",\s*t:"((?:[^"\\]|\\.)*)",\s*n:(\d+)\}', m.group(2))]
        out.append({'id': m.group(1), 'items': items})
    return out, full


# أسماء معروفة تُعرض كألقاب (ليست اقتباسات) — لا يُشترط أن تكون مطلع المتن
KNOWN_NAMES = {'آيَةُ الْكُرْسِيّ', 'الْمُعَوِّذَات', 'الْمُعَوِّذَات مَعَ النَّفْث', 'سَيِّدُ الِاسْتِغْفَارِ',
               'سَيِّدُ الِاسْتِغْفَار', 'الصَّلَاةُ الْإِبْرَاهِيمِيَّة', 'قِرَاءَةُ السَّجْدَةِ وَالْمُلْكِ'}

_TASHKEEL = re.compile('[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u0640]')


def _plain(t: str) -> str:
    """تطبيع للمقارنة: بلا تشكيل، بتوحيد رسم الحروف، وبلا ترقيم."""
    t = _TASHKEEL.sub('', t)
    for a, b in [('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ى', 'ي'), ('ئ', 'ي'),
                 ('ؤ', 'و'), ('ة', 'ه'), ('ﻻ', 'لا')]:
        t = t.replace(a, b)
    t = re.sub(r'[^\w\u0621-\u064A\s]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def check_titles_match_text() -> bool:
    """⑬ عنوان كل ذكر يطابق متنه:
       • الاقتباس (أي عنوان ليس اسمًا معروفًا) يجب أن يبدأ بمطلع المتن،
       • وكل مقطع فيه (بعد «…») يجب أن يوجد في المتن،
       • ولا تُقتبس كلمات من وسط النص كأنها مطلعه — وهو ما أزعج المستخدم في اللقطات."""
    print('⑬ مطابقة عنوان الذكر لمتنه (لا اقتباس من وسط النص)')
    sw = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    bad, checked = [], 0
    for st in parse_swift_sets(sw):
        for iid, text, target, full in st['items']:
            if not full or text in KNOWN_NAMES:
                continue
            checked += 1
            body = _plain(full.split('\n\n')[0])
            # العنوان: نُزيل لاحقة «(ثلاثًا)»/«(تمام المائة)» ثم نقسم على «…»
            title = re.sub(r'\s*\([^)]*\)\s*$', '', text).strip()
            parts = [p for p in (_plain(x) for x in title.split('…')) if p]
            if not parts:
                continue
            if not body.startswith(parts[0]):
                bad.append(f'{st["id"]}/{iid}: «{text}» لا يبدأ بمطلع المتن: {full.split(chr(10)+chr(10))[0][:60]}…')
                continue
            for seg in parts[1:]:
                if seg not in body:
                    bad.append(f'{st["id"]}/{iid}: «{text}» — مقطع «{seg}» ليس في المتن')
    print(f'   عُدّت عناوين اقتباسية: {checked}')
    for b in bad:
        print('   ✘ ' + b)
    if bad:
        return False
    print('   ✔ كل عنوان اقتباسي يطابق مطلع متنه ومقاطعه')
    return True


def check_no_fatima_tasbih() -> bool:
    """⑭ «تسبيح فاطمة» ليس من ألفاظ الكتاب (لا يُعرض نصًّا في التطبيق)."""
    print('⑭ خُلوّ الأذكار من «تسبيح فاطمة» (ليس من نصّ الكتاب)')
    bad = []
    for f in ['Shared.swift', 'simulator.html']:
        src = (ROOT / f).read_text(encoding='utf-8')
        for m in re.finditer('تسبيح فاطمة|فاطمة', src):
            line = src[:m.start()].count(chr(10)) + 1
            bad.append(f'{f}:{line}')
    for b in bad:
        print(f'   ✘ نصّ فيه «تسبيح فاطمة»: {b}')
    if bad:
        return False
    print('   ✔ لا وجود له في التطبيق ولا في المحاكي')
    return True


def check_dhikr_parity() -> bool:
    print('③ تطابق الأذكار كاملة (Swift ↔ المحاكي: المجموعة · الذكر · النص · العدد · النص الكامل)')
    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    sw = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    sw_sets = parse_swift_sets(sw)
    sim_sets, sim_full = parse_sim_sets(sim)

    bad = []
    if [x['id'] for x in sw_sets] != [x['id'] for x in sim_sets]:
        bad.append(f"ترتيب المجموعات مختلف: Swift {[x['id'] for x in sw_sets]} ↔ المحاكي {[x['id'] for x in sim_sets]}")
    else:
        for a, b in zip(sw_sets, sim_sets):
            if len(a['items']) != len(b['items']):
                bad.append(f"{a['id']}: عدد الأذكار Swift {len(a['items'])} ↔ المحاكي {len(b['items'])}")
                continue
            for (iid, text, target, full), (sid2, stext, starget) in zip(a['items'], b['items']):
                if iid != sid2:
                    bad.append(f"{a['id']}: المعرّف Swift «{iid}» ↔ المحاكي «{sid2}»")
                if text != stext:
                    bad.append(f"{a['id']}/{iid}: النص مختلف:\n      Swift: {text}\n      المحاكي: {stext}")
                if target != starget:
                    bad.append(f"{a['id']}/{iid}: العدد Swift {target} ↔ المحاكي {starget}")

    # النصوص الكاملة: كل نص في Swift له مدخل في FULL بالمفتاح نفسه، وبلا زيادة
    sw_full = {}
    for st in sw_sets:
        for iid, text, target, full in st['items']:
            if full:
                if text in sw_full and sw_full[text] != full:
                    bad.append(f'نصّان مختلفان لعنوان واحد: {text}')
                sw_full[text] = full
    for name in sorted(set(sw_full) - set(sim_full)):
        bad.append(f'✘ في Swift فقط: {name}')
    for name in sorted(set(sim_full) - set(sw_full)):
        bad.append(f'✘ في المحاكي فقط: {name}')
    for name in sorted(set(sim_full) & set(sw_full)):
        if sim_full[name] != sw_full[name]:
            bad.append(f'✘ النص الكامل مختلف في: {name}')

    n_items = sum(len(x['items']) for x in sw_sets)
    n_taps = sum(t for st in sw_sets for _, _, t, _ in st['items'])
    print(f'   المجموعات: {len(sw_sets)} · الأذكار: {n_items} · الضغطات: {n_taps}')
    print(f'   النصوص الكاملة: Swift {len(sw_full)} · المحاكي {len(sim_full)}')
    for b in bad:
        print('   ✘ ' + b)
    if bad:
        return False
    print('   ✔ المجموعات والأذكار والنصوص مطابقة تمامًا بين الطرفين')
    return True


def check_model_members() -> bool:
    """يتأكد أن كل مرجع `model.x` و`session.x` في الواجهات موجود فعلًا في النموذجين.
       هذا يلتقط خطأ الإملاء في اسم خاصية — وهو أكثر خطأ يوقف الترجمة."""
    print('④ مراجع النماذج (model.x / session.x)')

    def members(path):
        src = re.sub(r'/\*.*?\*/', '', path.read_text(encoding='utf-8'), flags=re.S)
        src = '\n'.join(l[:l.find('//')] if '//' in l else l for l in src.splitlines())
        names = set(re.findall(r'(?:var|let)\s+(\w+)', src))
        names |= set(re.findall(r'func\s+(\w+)', src))
        names |= set(re.findall(r'case\s+(\w+)', src))
        return names

    cm = members(ROOT / 'CounterModel.swift')
    sm = members(ROOT / 'SessionManager.swift')
    bad = []
    for f in ['CounterView.swift', 'ReadingView.swift', 'OptionsPanel.swift',
              'MenuView.swift', 'TasbihApp.swift', 'SetBackgrounds.swift']:
        p = ROOT / f
        if not p.exists():
            continue
        src = p.read_text(encoding='utf-8')
        for m in re.finditer(r'\bmodel\.(\w+)', src):
            if m.group(1) not in cm:
                bad.append(f'{f}: model.{m.group(1)}')
        for m in re.finditer(r'\bsession\.(\w+)', src):
            if m.group(1) not in sm:
                bad.append(f'{f}: session.{m.group(1)}')
    if bad:
        for b in sorted(set(bad)):
            print('   ✘ ' + b)
        return False
    print(f'   ✔ لا مراجع مفقودة (CounterModel: {len(cm)} عضوًا · SessionManager: {len(sm)})')
    return True


def check_risky_apis() -> bool:
    """⓺ رموز محرّمة + واجهات سبق أن أوقفت الترجمة.
       (درس: `.gestureButton` غير موجودة في HandGestureShortcut ⇒ ٤ أخطاء في أول بناء على أبل.)"""
    print('⑥ واجهات محرّمة ومكرّرة (سبب فشل الترجمة الأول)')

    forbidden = {
        '.gestureButton': 'غير موجودة في HandGestureShortcut (الوحيدة: .primaryAction)',
        'SharedCounter.increment(': 'دالة محذوفة — الصحيح SharedCounter.tap()',
        'SettingsView(': 'شاشة محذوفة من المشروع',
        'menuAction': 'الاسم الصحيح menuAct',
    }
    files = sorted(list(ROOT.glob('*.swift')) + list((ROOT / 'Widget').glob('*.swift')))
    bad = []
    for f in files:
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('//')[0]
            for sym, why in forbidden.items():
                if sym in code:
                    bad.append(f'{f.name}:{i} → {sym} ({why})')
    # كل استدعاء للإيماءة يجب أن يكون .primaryAction حصرًا
    for f in files:
        for m in re.finditer(r'handGestureShortcut\(\s*\.(\w+)', f.read_text(encoding='utf-8')):
            if m.group(1) != 'primaryAction':
                bad.append(f'{f.name}: handGestureShortcut(.{m.group(1)}) — الوحيدة المدعومة: .primaryAction')
    # تصريحات مكرّرة في نفس الهدف = خطأ ترجمة مؤكّد
    seen = {}
    for f in files:
        src = re.sub(r'//.*', '', f.read_text(encoding='utf-8'))
        for m in re.finditer(r'^(?:public |internal |private |final )*(?:struct|enum|class|actor)\s+(\w+)', src, re.M):
            seen.setdefault(m.group(1), []).append(f.name)
    for name, where in seen.items():
        if len(set(where)) > 1:
            bad.append(f'تصريح مكرّر: {name} في {sorted(set(where))}')

    # (درس ٢) وزن الخط في SwiftUI يقبل == فقط — لا >= ولا <=  ⇒ خطأ ترجمة مؤكّد
    for f in files:
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('//')[0]
            if re.search(r'[<>]=\s*\.(?:ultraLight|thin|light|regular|medium|semibold|bold|heavy|black)\b', code):
                bad.append(f'{f.name}:{i} — Font.Weight لا يقبل المقارنة (≥/≤)؛ استعمل == أو قائمة contains')

    # (درس ٣) كل ملف يستعمل واجهة UIKit يجب أن يُعلن `import UIKit` بنفسه
    for f in files:
        code = re.sub(r'//.*', '', f.read_text(encoding='utf-8'))
        if re.search(r'\b(?:UIFont|UIColor|UIImage|UIScreen)\b', code) and 'import UIKit' not in code:
            bad.append(f'{f.name} — يستعمل واجهات UIKit بلا «import UIKit» في الملف نفسه')

    if bad:
        for b in bad:
            print('   ✘ ' + b)
        return False
    n_calls = sum(len(re.findall(r'handGestureShortcut\(', f.read_text(encoding='utf-8'))) for f in files)
    print(f'   ✔ لا رموز محرّمة · لا تصريحات مكرّرة · {n_calls} استدعاء إيماءة (كلها .primaryAction)')
    return True


def check_assets_and_sources() -> bool:
    """⑧ الخطوط والأصوات + اكتمال قوائم المصادر في ملفي المشروع.
       (درس: ملف جديد لا يُضاف لـ project.yml = ترجمة تفشل بأن «الرمز غير موجود».)"""
    print('⑧ الخطوط والأصوات + اكتمال المصادر')

    ok_all = True

    # ── الخطوط: الملفات موجودة ومُعلنة في UIAppFonts في الملفين ──
    fonts = ['Amiri-Regular.ttf', 'Amiri-Bold.ttf', 'Almarai-Regular.ttf', 'Almarai-Bold.ttf']
    for f in fonts:
        if not (ROOT / 'Fonts' / f).exists():
            print(f'   ✘ ملف الخط مفقود: Fonts/{f}'); ok_all = False
    for yml in ['project.yml', 'project-container.yml']:
        src = (ROOT / yml).read_text(encoding='utf-8')
        if 'UIAppFonts' not in src:
            print(f'   ✘ {yml}: لا توجد قائمة UIAppFonts'); ok_all = False
        for f in fonts:
            # يجب أن يكون الاسم داخل قسم UIAppFonts (تحقّق بسيط: موجود في الملف بعد كلمة UIAppFonts)
            if src.find('UIAppFonts') >= 0 and f not in src[src.find('UIAppFonts'):src.find('UIAppFonts') + 400]:
                print(f'   ✘ {yml}: الخط {f} غير مُعلن في UIAppFonts'); ok_all = False
        if 'Fonts' not in src:
            print(f'   ✘ {yml}: مجلد Fonts غير مضاف إلى مصادر الهدف'); ok_all = False
    if ok_all:
        print(f'   ✔ {len(fonts)} خطوط مرفقة ومُعلنة في الملفين')

    # ── الأصوات: الملفات موجودة ومضافة للمصادر ومرتبطة في Sounds.swift ──
    sounds = ['click_soft.wav', 'chime_soft.wav']
    for f in sounds:
        if not (ROOT / 'Sounds' / f).exists():
            print(f'   ✘ ملف صوت مفقود: Sounds/{f}'); ok_all = False
    code = (ROOT / 'Sounds.swift').read_text(encoding='utf-8')
    for stem in ['click_soft', 'chime_soft']:
        if stem not in code:
            print(f'   ✘ Sounds.swift لا يشير إلى {stem}'); ok_all = False
    for yml in ['project.yml', 'project-container.yml']:
        if '- path: Sounds' not in (ROOT / yml).read_text(encoding='utf-8'):
            print(f'   ✘ {yml}: مجلد Sounds غير مضاف للمصادر'); ok_all = False
    if ok_all:
        print(f'   ✔ {len(sounds)} ملفات صوت مرفقة ومربوطة')

    # ── اكتمال المصادر: كل ملف Swift في الجذر يجب أن يكون في ملفي المشروع ──
    swift_files = sorted(f.name for f in ROOT.glob('*.swift'))
    for yml in ['project.yml', 'project-container.yml']:
        src = (ROOT / yml).read_text(encoding='utf-8')
        missing = [f for f in swift_files if f not in src]
        if missing:
            print(f'   ✘ {yml}: ملفات غير مُضافة: {missing}'); ok_all = False
    if ok_all:
        print(f'   ✔ كل ملفات Swift ({len(swift_files)}) مُضافة في ملفي المشروع')

    # ── عدد المجموعات متطابق بين Swift والمحاكي ──
    sw = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    sw_sets = len(re.findall(r'^    DhikrSet\(', sw, re.M))
    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    sim_block = sim[sim.find('const SETS = ['):sim.find('\n];', sim.find('const SETS = ['))]
    sim_sets = len(re.findall(r'\{ id:"', sim_block))
    if sw_sets != sim_sets or sw_sets < 8:
        print(f'   ✘ عدد المجموعات مختلف: Swift {sw_sets} · المحاكي {sim_sets}'); ok_all = False
    else:
        print(f'   ✔ عدد المجموعات متطابق: {sw_sets} في الاثنين')

    return ok_all


def check_app_group() -> bool:
    print('⑨ صلاحية مجموعة التطبيق (App Group)')
    try:
        import yaml
    except ImportError:
        print('   ⚠ PyYAML غير مثبّت — تخطّي')
        return True
    shared = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    m = re.search(r'appGroupID\s*=\s*"([^"]+)"', shared)
    want = m.group(1) if m else None
    print(f'   المعرّف في Shared.swift: {want}')
    ok = True
    for name in ['project.yml', 'project-container.yml']:
        p = ROOT / name
        if not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        for tname, t in (d.get('targets') or {}).items():
            srcs = [x if isinstance(x, str) else x.get('path', '') for x in (t.get('sources') or [])]
            if not any('Shared.swift' in str(x) for x in srcs):
                continue                      # لا يستخدم الكود المشترك ⇒ لا يحتاج الصلاحية
            groups = (((t.get('entitlements') or {}).get('properties') or {})
                      .get('com.apple.security.application-groups')) or []
            if want in groups:
                print(f'   ✔ {name} · {tname}')
            else:
                ok = False
                print(f'   ✘ {name} · {tname}: صلاحية مجموعة التطبيق مفقودة أو مختلفة')
    if ok:
        print('   ✔ كل هدف يقرأ الكود المشترك يملك الصلاحية نفسها')
    return ok


def check_scheme_runnable() -> bool:
    """⑩ هدف التشغيل في كل مخطط.

    درس من فحص الترجمة (exit 70): XcodeGen **يرتّب أهداف المخطط أبجديًا** ويربط
    هدف التشغيل بأول هدف قابل للتشغيل — لا باسم المخطط. ففي ملف الحاوية:
    «Tasbih» (ساعة) تأتي قبل «TasbihContainer» (آيفون) ⇒ يصبح المخطط «ساعة»
    ويقول xcodebuild: «لا توجد وجهة iOS». الحلّ: `run.executable` في المخطط."""
    print('⑩ هدف التشغيل في المخططات (سبب فشل الترجمة الثاني)')
    try:
        import yaml
    except ImportError:
        print('   ⚠ PyYAML غير مثبّت — تخطّي')
        return True

    expected = {
        'project.yml':           {'Tasbih': 'Tasbih'},
        'project-container.yml': {'TasbihContainer': 'TasbihContainer', 'Tasbih': 'Tasbih'},
    }
    ok = True
    for name, want in expected.items():
        p = ROOT / name
        if not p.exists():
            continue
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        targets = d.get('targets') or {}
        for scheme, exe in want.items():
            sch = (d.get('schemes') or {}).get(scheme)
            if sch is None:
                ok = False
                print(f'   ✘ {name}: المخطط «{scheme}» مفقود')
                continue
            for t in (sch.get('build', {}).get('targets') or {}):
                if t not in targets:
                    ok = False
                    print(f'   ✘ {name} · مخطط {scheme}: الهدف «{t}» غير موجود في الملف')
            got = (sch.get('run') or {}).get('executable')
            if got == exe:
                print(f'   ✔ {name} · مخطط {scheme} ⇒ هدف التشغيل: {got}')
            else:
                ok = False
                print(f'   ✘ {name} · مخطط {scheme}: run.executable = {got!r} (المطلوب {exe!r})'
                      ' — بدونه يختار XcodeGen هدفًا أبجديًا خاطئًا ⇒ «لا توجد وجهة»')
    return ok


def check_debug_shots() -> bool:
    """⑪ مدخل لقطات المتجر لا يتسرّب إلى نسخة المتجر.

    `DebugShots.swift` محصور بالكامل بين #if DEBUG و #endif (يُحذف من نسخة
    المتجر). وأي استعمال لِـ SabhaShot في ملف آخر يجب أن يكون هو الآخر داخل
    #if DEBUG — وإلا فشلت ترجمة نسخة Release بأن «الرمز غير موجود».
    (لقطة الودجت في المتجر لا تكفي: هذا فحص يمنع مفاجأة وقت النشر.)"""
    print('⑪ مدخل لقطات المتجر (لا يتسرّب إلى نسخة المتجر)')
    shots = ROOT / 'DebugShots.swift'
    if not shots.exists():
        print('   ⚠ DebugShots.swift غير موجود — تخطّي')
        return True
    src = shots.read_text(encoding='utf-8')
    ok = True
    # نعدّ أسطر التوجيه نفسها (لا الإشارات داخل التعليقات)
    dirs_if = sum(1 for ln in src.splitlines() if ln.strip() == '#if DEBUG')
    dirs_end = sum(1 for ln in src.splitlines() if ln.strip() == '#endif')
    if dirs_if < 1 or dirs_if != dirs_end:
        ok = False
        print(f'   ✘ DebugShots.swift: توجيهات غير متوازنة (#if DEBUG: {dirs_if} · #endif: {dirs_end})')

    files = sorted(list(ROOT.glob('*.swift')) + list((ROOT / 'Widget').glob('*.swift')))
    offenders = []
    for f in files:
        if f.name == 'DebugShots.swift':
            continue
        depth = 0
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            stripped = line.strip()
            if stripped == '#if DEBUG':
                depth += 1
            elif stripped == '#endif' and depth > 0:
                depth -= 1
            if 'SabhaShot' in line.split('//')[0] and depth == 0:
                offenders.append(f'{f.name}:{i}')
    if offenders:
        ok = False
        for o in offenders:
            print(f'   ✘ {o}: استعمال SabhaShot خارج #if DEBUG')
    if ok:
        uses = sum(len(re.findall(r'SabhaShot', (ROOT / f).read_text(encoding='utf-8')))
                   for f in ['TasbihApp.swift', 'CounterView.swift', 'MenuView.swift']
                   if (ROOT / f).exists())
        print(f'   ✔ SabhaShot محصور في #if DEBUG ({uses} استعمالًا في التطبيق)')
    return ok


def check_single_menu_button() -> bool:
    """⑫ زر واحد للقائمة (لا ازدواج).

    كان للقائمة زرّان: «☰» أعلى اليسار + «☰ القائمة» أسفل الشاشة — وهو تكرار
    طلبه المستخدم إزالته. وُحّدا في زر واحد أسفل الشاشة (في التطبيق والمحاكي).
    هذا الفحص يمنع عودة الازدواج في أي تعديل لاحق."""
    print('⑫ زر واحد للقائمة (لا ازدواج)')
    ok = True

    cv = (ROOT / 'CounterView.swift').read_text(encoding='utf-8')
    icons = len(re.findall(r'line\.3\.horizontal', cv))
    if icons != 1:
        ok = False
        print(f'   ✘ CounterView.swift: عدد أيقونات ☰ = {icons} (المطلوب ١ فقط)')
    # لا يجوز أن تحمل ☰ في شريط الأدوات العلوي (لكن يُسمح بعناصر أخرى هناك)
    for m in re.finditer(r'ToolbarItem\(placement: \.topBarTrailing\)', cv):
        if 'line.3.horizontal' in cv[m.start():m.start() + 400]:
            ok = False
            print('   ✘ CounterView.swift: يوجد ☰ في شريط الأدوات العلوي (يجب أن تكون أسفل الشاشة)')
    # ويجب أن تكون داخل صف الأدوات السفلي
    if cv.find('private var controlRow') == -1 or cv.find('line.3.horizontal') < cv.find('private var controlRow'):
        ok = False
        print('   ✘ CounterView.swift: ☰ ليست داخل صف الأدوات السفلي')

    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    if 'id="menuBtn"' in sim:
        ok = False
        print('   ✘ simulator.html: زر ☰ العلوي (menuBtn) ما زال موجودًا')
    n_menu = sim.count('id="btnMenu"')
    if n_menu != 1:
        ok = False
        print(f'   ✘ simulator.html: عدد أزرار «☰ القائمة» = {n_menu} (المطلوب ١)')

    if ok:
        print('   ✔ زر واحد فقط: «☰ القائمة» أسفل الشاشة — في التطبيق والمحاكي')
    return ok


def check_counting_mode_saved() -> bool:
    """⑮ طريقة العدّ تُحفظ وتبقى عند كل فتح للتطبيق + خيارها في الشاشة الرئيسية.

    الطلب: «خيار اختيار طريقة العدّ في الشاشة الرئيسية، ويُحتفظ به عند كل فتح».
    نتحقّق نصًّا أن:
      ① الاختيار يُخزَّن في ذاكرة الجهاز (d.set … SharedKeys.countingMode) داخل save()
      ② الحالة تُقرأ عند الإقلاع (init) بـ SharedKeys.countingMode
      ③ save() تُستدعى من setCountingMode (وإلا ضاع الاختيار)
      ④ الشاشة الرئيسية فيها أزرار الأوضاع الثلاثة + تُحفظ تلقائيًا (HomeView)
      ⑤ المحاكي يفعل المثل (localStorage) في صدق السلوك."""
    print('⑮ طريقة العدّ: تُختار من الشاشة الرئيسية وتُحفظ فتبقى عند كل فتح')
    ok = True
    model = (ROOT / 'CounterModel.swift').read_text(encoding='utf-8')
    save = model[model.find('private func save()'):]
    save = save[:save.find('\n    }')]
    if 'SharedKeys.countingMode' not in save or 'countingMode.rawValue' not in save:
        ok = False
        print('   ✘ CounterModel.save(): طريقة العدّ لا تُخزَّن (SharedKeys.countingMode)')
    init = model[model.find('init()'):]
    init = init[:init.find('\n    }')]
    if 'SharedKeys.countingMode' not in init:
        ok = False
        print('   ✘ CounterModel.init(): طريقة العدّ لا تُقرأ عند الإقلاع')
    setm = model[model.find('func setCountingMode'):]
    setm = setm[:setm.find('\n    }')]
    if 'save()' not in setm:
        ok = False
        print('   ✘ setCountingMode(): لا تستدعي save() ⇒ الاختيار يضيع عند الإغلاق')

    home = (ROOT / 'HomeView.swift').read_text(encoding='utf-8')
    modes = ['.doubleTap', '.motion', '.crown']
    if not all(m in home for m in modes) or 'setCountingMode' not in home:
        ok = False
        print('   ✘ HomeView.swift: أزرار الأوضاع الثلاثة (نقرة · حركة · تاج) غير كاملة')
    if 'طريقة العدّ' not in home:
        ok = False
        print('   ✘ HomeView.swift: لا يوجد صفّ «طريقة العدّ» في الشاشة الرئيسية')

    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    if "data-mode=\"0\"" not in sim or "data-mode=\"2\"" not in sim or 'sabha.cMode' not in sim:
        ok = False
        print('   ✘ simulator.html: صفّ طريقة العدّ أو حفظها (localStorage) غير موجود')

    if ok:
        print('   ✔ الأوضاع الثلاثة في الشاشة الرئيسية · تُخزَّن في ذاكرة الجهاز وتُقرأ عند الإقلاع')
    return ok


def check_rating_feedback() -> bool:
    """⑯ التقييم والملاحظات: صفحة داخل القائمة + روابط صحيحة (قول الحقائق عن watchOS).

    الطلب: «أين تقييم المستخدم ورفع الملاحظات؟» ⇒ نتحقّق أن الميزة موجودة فعلًا:
      ① Shared.swift فيه AppLinks: رابط التقييم (write-review) + بريد/صفحة الدعم
      ② الرابط بصيغة أبل المعتمدة ولا يُفتح إن كان المعرّف الرقمي فارغًا (حماية)
      ③ OptionsPanel فيه صفحة `.support` وزرّان (تقييم · ملاحظة) وخطوة تشخيص بالإصدار
      ④ المحاكي فيه نفس الصفحة وزرّاها (صدق السلوك في العرض التوضيحي)
      ⑤ لا نداء لتقييم داخل التطبيق: watchOS لا يملك نافذة تقييم — فلا نَدّعي غير ذلك."""
    print('⑯ التقييم والملاحظات: موجودة في القائمة بروابط صحيحة')
    ok = True
    # ملاحظة: لا نُجرّد التعليقات هنا لأن رابط أبل نفسه فيه `//` (وإلا قُطع الرابط)
    shared = (ROOT / 'Shared.swift').read_text(encoding='utf-8')
    if 'enum AppLinks' not in shared:
        ok = False; print('   ✘ Shared.swift: لا يوجد enum AppLinks')
    for need, msg in [('apps.apple.com/app/id', 'رابط App Store غير موجود'),
                      ('action=write-review', 'رابط كتابة التقييم (write-review) غير موجود'),
                      ('supportPage', 'رابط صفحة الدعم غير موجود'),
                      ('versionLine', 'سطر الإصدار (للتشخيص) غير موجود'),
                      ('CFBundleShortVersionString', 'سطر الإصدار لا يقرأه من معلومات التطبيق')]:
        if need not in shared:
            ok = False; print('   ✘ Shared.swift: ' + msg)
    # حماية: لا يُفتح رابط تقييم بمعرّف فارغ أو غير رقمي
    if 'trimmingCharacters' not in shared or 'allSatisfy' not in shared or 'reviewURL != nil' not in shared:
        ok = False; print('   ✘ Shared.swift: لا حماية من معرّف App Store الفارغ/غير الرقمي')

    panel = strip_comments((ROOT / 'OptionsPanel.swift').read_text(encoding='utf-8'))
    if 'case main, sets, widget, support' not in panel:
        ok = False; print('   ✘ OptionsPanel: صفحة .support غير مضافة إلى PanelPage')
    for need, msg in [('supportPage', 'لا يوجد محتوى صفحة التقييم'),
                      ('openReview()', 'لا يوجد زرّ التقييم (openReview)'),
                      ('openSupport()', 'لا يوجد زرّ الملاحظة (openSupport)'),
                      ('openURL', 'لا يستعمل openURL لفتح الرابط'),
                      ('AppLinks.versionLine', 'لا يعرض رقم الإصدار')]:
        if need not in panel:
            ok = False; print('   ✘ OptionsPanel: ' + msg)
    if 'star.bubble' not in panel or 'page = .support' not in panel:
        ok = False; print('   ✘ OptionsPanel: لا بند في الصفحة الرئيسية يفتح صفحة التقييم')
    # صدق: لا ندّعي تقييمًا داخليًا (لا SKStoreReviewController في تطبيق ساعة)
    if 'SKStoreReviewController' in panel:
        ok = False; print('   ✘ OptionsPanel: يستعمل SKStoreReviewController — لا يوصل لشيء في watchOS')
    # حماية من «الاستبدال الخاطئ»: ملاحظة طريقة العدّ (شاشة مضيئة) يجب أن تبقى قائمة
    if 'النقرة المزدوجة تحتاج شاشة مضيئة' not in panel:
        ok = False; print('   ✘ OptionsPanel: ملاحظة «النقرة المزدوجة تحتاج شاشة مضيئة» ضاعت (استبدال خاطئ؟)')

    sim = (ROOT / 'simulator.html').read_text(encoding='utf-8')
    for need, msg in [("'support'", 'صفحة الدعم غير موجودة في المحاكي'),
                      ("'rate'", 'زرّ التقييم غير موجود في المحاكي'),
                      ("'supportMail'", 'زرّ الملاحظة غير موجود في المحاكي'),
                      ('التقييم والملاحظات', 'اسم البند غير مطابق')]:
        if need not in sim:
            ok = False; print('   ✘ simulator.html: ' + msg)

    proj = (ROOT / 'project.yml').read_text(encoding='utf-8')
    if 'CURRENT_PROJECT_VERSION: "2"' not in proj:
        ok = False; print('   ✘ project.yml: رقم البناء يجب أن يكون ٢ (الإصدار الأول المحدَّث)')
    if 'MARKETING_VERSION: "1.0"' not in proj:
        ok = False; print('   ✘ project.yml: رقم الإصدار العام يجب أن يبقى 1.0 (أول إصدار)')

    if ok:
        print('   ✔ الصفحة موجودة · رابط write-review صحيح · رقم الإصدار يظهر · بلا نداء تقييم وهمي')
    return ok


if __name__ == '__main__':
    ok_all = (check_apis() and check_sources() and check_dhikr_parity()
              and check_model_members() and check_risky_apis()
              and check_assets_and_sources() and check_app_group()
              and check_scheme_runnable() and check_debug_shots()
              and check_titles_match_text() and check_no_fatima_tasbih()
              and check_single_menu_button()
              and check_counting_mode_saved()
              and check_rating_feedback())
    print()
    print('📊 النتيجة:', '✔ كل الفحوصات سليمة' if ok_all else '❌ توجد مشاكل أعلاه')
    sys.exit(0 if ok_all else 1)
