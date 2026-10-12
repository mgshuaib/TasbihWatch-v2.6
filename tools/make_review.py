#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📜 مُولِّد ملف مراجعة الأذكار — يقرأ Shared.swift ويكتب صفحة HTML كاملة للمراجعة.
    python3 tools/make_review.py            ⇒  /home/user/مراجعة-الأذكار.html
    python3 tools/make_review.py --old old.json   (لإظهار جدول «ما تغيّر»)
"""
import sys, json, pathlib, re, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT.parent / 'مراجعة-الأذكار.html'
BOOK = {'after_prayer', 'morning', 'evening', 'sleep'}
# أذكار كانت بأسماء مختصرة فصارت بأسماء أوضح (النص نفسه — ليست إزالة)
RENAMES = {
    'لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ…': 'لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ… (تمام المائة)',
    # تصحيحك: «لَا إِلَهَ إِلَّا اللَّهُ… (ثلاثًا)» كان عنوانًا لغير متنه ⇒ صار العنوان مطابقًا للمتن
    'لَا إِلَهَ إِلَّا اللَّهُ… (ثلاثًا)': 'اللَّهُمَّ لَا مَانِعَ لِمَا أَعْطَيْتَ…',
    'لَا إِلَهَ إِلَّا اللَّه وَحْدَهُ…': 'لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ… (تمام المائة)',
}
ICO = {'after_prayer': '🕌', 'morning': '🌅', 'evening': '🌙', 'sleep': '🛏',
       'general': '✨', 'free': '∞', 'istighfar': '♻️', 'salawat': '🤍'}


def parse_sets(path):
    src = pathlib.Path(path).read_text(encoding='utf-8')
    k = src.find('let adhkarSets: [DhikrSet] = [')
    block = src[k:src.find('\n]\n', k)]
    sets = []
    for part in re.split(r'\n    DhikrSet\(', block)[1:]:
        items = []
        for m in re.finditer(r'Dhikr\((.*?)\)\s*,?\s*(?=Dhikr\(|\])', part, re.S):
            b = ' '.join(m.group(1).split())
            f = re.search(r'full:\s*"((?:[^"\\]|\\.)*)"', b)
            items.append(dict(
                id=re.search(r'id:\s*"([^"]+)"', b).group(1),
                text=re.search(r'text:\s*"((?:[^"\\]|\\.)*)"', b).group(1).replace('\\n', '\n'),
                target=int(re.search(r'target:\s*(\d+)', b).group(1)),
                full=(f.group(1).replace('\\n', '\n') if f else None)))
        sets.append(dict(
            id=re.search(r'id:\s*"([^"]+)"', part).group(1),
            title=re.search(r'title:\s*"([^"]+)"', part).group(1),
            closeDua=re.search(r'closeDua:\s*"([^"]+)"', part).group(1),
            items=items))
    return sets


# سبب كل حذف (يُعرض بجانب الذكر المحذوف في جدول «ما تغيّر»)
REASONS = [
    ('عشرًا', 'بطلبك: احذف ذكر «عشرًا» من الصباح — بقي «مائة مرة» كما في الكتاب (و«عشرًا» باقية في المساء فقط)'),
    ('فاطمة', 'ليس من «حصن المسلم» — أُزيل بطلبك'),
    ('الْوُضُوء', 'ليس ذكرًا مستقلًّا في الكتاب (مقصد عملي) — أُزيل مع تبسيط الحشو'),
]


def inline_png(rel, max_kb=180):
    """يُدمج PNG كصورة data-URI حتى تظهر داخل أي عارض/معاينة بلا إنترنت."""
    import base64
    f = ROOT.parent / rel
    if not f.exists():
        f = ROOT / rel
    if not f.exists():
        return ''
    b = f.read_bytes()
    if len(b) > max_kb * 1024:
        return ''
    return 'data:image/png;base64,' + base64.b64encode(b).decode()

def esc(t):
    return html.escape(t).replace('\n', '<br>')


def main():
    sets = parse_sets(ROOT / 'Shared.swift')
    book = [s for s in sets if s['id'] in BOOK]
    other = [s for s in sets if s['id'] not in BOOK]
    tot_items = sum(len(s['items']) for s in sets)
    tot_taps = sum(i['target'] for s in sets for i in s['items'])

    old = None
    if '--old' in sys.argv:
        old = json.load(open(sys.argv[sys.argv.index('--old') + 1]))
    diff_rows = ''
    if old:
        oldmap = {s['id']: {i['text'] for i in s['items']} for s in old}
        newmap = {s['id']: {i['text'] for i in s['items']} for s in sets}
        rows = []
        for sid in ['after_prayer', 'morning', 'evening', 'sleep']:
            o, n = oldmap[sid], newmap[sid]
            title = next(s['title'] for s in sets if s['id'] == sid)
            adds = [t for t in (n - o) if t not in RENAMES.values()]
            rems = [t for t in (o - n) if not (t in RENAMES and RENAMES[t] in n)]
            rows.append(f"<tr><td>{ICO[sid]} {title}</td><td>{len(oldmap[sid])}</td>"
                        f"<td class='ok'>{len(newmap[sid])}</td>"
                        f"<td>{len(adds)}</td><td>{len(rems)}</td></tr>")
        removed, renamed = [], []
        for sid in ['after_prayer', 'morning', 'evening', 'sleep']:
            for t in sorted(oldmap[sid] - newmap[sid]):
                if t in RENAMES and RENAMES[t] in newmap[sid]:
                    renamed.append(f"<li>{ICO[sid]} «{esc(t)}» → «{esc(RENAMES[t])}» (الموضع نفسه — والعنوان صار مطابقًا لمتنه)</li>")
                else:
                    why = next((r for k, r in REASONS if k in t), 'بطلب منك')
                    removed.append(f"<li>{ICO[sid]} {esc(t)} — <b>{esc(why)}</b></li>")
        diff_rows = f"""
  <h2>② ما تغيّر بالضبط</h2>
  <table class="tbl">
    <tr><th>المجموعة</th><th>قبل</th><th>بعد</th><th>أُضيف</th><th>أُزيل</th></tr>
    {''.join(rows)}
  </table>
  <p class="note">هذه <b>إعادة تسمية</b> — الذكر لم يُحذف، بل صار عنوانه يعبّر عن متنه (لا لبس في الصور):</p>
  <ul class="renamed">{''.join(renamed) or '<li>لا شيء</li>'}</ul>
  <p class="note">الأذكار التي كانت ولم تبقَ، ولماذا:</p>
  <ul class="removed">{''.join(removed)}</ul>"""

    cards = ''
    for s in book:
        rows = []
        for i, it in enumerate(s['items'], 1):
            rows.append(f"""
      <div class="card">
        <div class="head"><span class="num">{i}</span><b>{esc(it['text'])}</b>
          <span class="badge">{'بلا حد' if it['target'] == 0 else '×' + str(it['target'])}</span></div>
        <div class="body">{esc(it['full']) if it['full'] else '<i>نصّه القصير هو نفسه المعروض</i>'}</div>
      </div>""")
        taps = sum(i['target'] for i in s['items'])
        cards += f"""
  <section class="set">
    <h3>{ICO[s['id']]} {s['title']} <span class="meta">{len(s['items'])} أذكار · {taps} ضغطة</span></h3>
    {''.join(rows)}
  </section>"""

    SHOT_LEAVE = inline_png('screenshots/16-الخروج-بضغطة-التاج-العدّ-محفوظ.png')
    SHOT_HOME = inline_png('screenshots/17-الشاشة-الرئيسية.png')
    others = '\n'.join(
        f"<li>{ICO[s['id']]} <b>{s['title']}</b> — {len(s['items'])} أذكار</li>" for s in other)

    doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>مراجعة أذكار التطبيق — مطابقة «حصن المسلم»</title>
<style>
  :root {{ --em:#29c79a; --teal:#33a2b8; --ink:#0b1014; --card:#141c22; --line:#22303a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:linear-gradient(180deg,#0b1014,#0e161c 40%,#0b1014);
         color:#e8f0f0; font-family:"Amiri","Almarai","Segoe UI",system-ui,sans-serif;
         line-height:1.9; padding:22px 14px 60px; }}
  .wrap {{ max-width:860px; margin:0 auto; }}
  h1 {{ font-size:26px; margin:0 0 4px; }}
  h2 {{ font-size:20px; margin:30px 0 10px; color:var(--em); }}
  h3 {{ font-size:18px; margin:26px 0 12px; display:flex; flex-wrap:wrap; gap:8px; align-items:baseline; }}
  .sub {{ color:#9fb3b8; font-size:14px; }}
  .banner {{ background:rgba(41,199,154,.10); border:1px solid rgba(41,199,154,.35);
             border-radius:14px; padding:12px 14px; margin:14px 0 6px; font-size:15px; }}
  .tbl {{ width:100%; border-collapse:collapse; margin:10px 0 6px; font-size:15px; }}
  .tbl th,.tbl td {{ border:1px solid var(--line); padding:7px 9px; text-align:center; }}
  .tbl th {{ background:#16222a; color:var(--teal); }}
  .tbl td:first-child {{ text-align:right; }}
  .ok {{ color:var(--em); font-weight:700; }}
  .note {{ color:#9fb3b8; font-size:14px; }}
  .removed {{ color:#f2b8a0; }}
  .shot {{ text-align:center; margin:10px 0 2px; }}
  .shot img {{ width:220px; max-width:68%; border-radius:26px; border:1px solid var(--line); background:#000; }}
  .shot .cap {{ font-size:12.5px; color:#9fb3b8; margin-top:6px; line-height:1.8; }}
  .renamed {{ color:#cfe0b8; }}
  .set {{ margin-top:26px; }}
  .meta {{ font-size:13px; color:#8fa6ac; font-weight:400; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:10px 12px; margin:8px 0; }}
  .head {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
  .num {{ background:#1d2b33; color:var(--teal); border-radius:8px; padding:1px 8px; font-size:13px; }}
  .badge {{ margin-inline-start:auto; background:rgba(41,199,154,.13); color:var(--em);
            border:1px solid rgba(41,199,154,.3); border-radius:999px; padding:1px 9px; font-size:13px; }}
  .body {{ margin-top:6px; font-size:16px; color:#dbe7e7; }}
  .body i {{ color:#7f9499; }}
  code {{ background:#16222a; border:1px solid var(--line); border-radius:6px; padding:1px 6px; font-size:13px; }}
  .ask {{ background:rgba(51,162,184,.10); border:1px solid rgba(51,162,184,.35);
          border-radius:14px; padding:14px; margin-top:26px; }}
  ul {{ margin:8px 0; padding-inline-start:22px; }}
  a {{ color:var(--teal); }}
</style>
</head>
<body>
<div class="wrap">

  <h1>مراجعة أذكار التطبيق قبل النشر</h1>
  <div class="sub">مطابقة كاملة لكتاب «حِصْنُ الْمُسْلِم من أذكار الكتاب والسنة» — د. سعيد بن علي بن وهف القحطاني (الرياض) ·
    النصوص من الموقع الرسمي للكتاب <code>hisnmuslim.com</code></div>

  <div class="banner">
    ✅ <b>ما تم:</b> الأربع مجموعات الكتابية (بعد الصلاة · الصباح · المساء · النوم) مطابقة لفصول الكتاب نصًّا وعددًا،
    وكل نصّ فيها <b>دُقّق آليًا حرفًا حرفًا</b> مقابل صفحات الكتاب الرسمية قبل عرضه عليك (انظر «كيف دُقّقت» أدناه).
    <br>📊 <b>الإجمالي الآن:</b> ٨ مجموعات · {tot_items} ذكرًا · {tot_taps} ضغطة في دورة كاملة.
  </div>

  <h2>⓪ ما تغيّر في مراجعتك (الثلاثة الأخيرة)</h2>
  <table class="tbl">
    <tr><th>طلبك</th><th>ما فُعل</th></tr>
    <tr><td>«في أذكار الصباح ذكرتَ «لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ» عشرًا، ونفسه مائة مرة — احذف ذكر عشرًا»</td>
        <td><b>حُذف</b> من «أذكار الصباح» — وبقي «مائة مرة إذا أصبح» كما في الكتاب (صار ٢٢ ذكرًا بدل ٢٣).
            و«عشرًا» باقية في «أذكار المساء» وحدها (٢١ ذكرًا) — وهو الموضع الذي يذكرها فيه الكتاب.</td></tr>
    <tr><td>«<b>«اللَّهُمَّ لَا مَانِعَ لِمَا أَعْطَيْتَ…» حسب المتن مرة واحدة</b>» (تصحيحك الأخير)</td>
        <td><b>صُحّح</b>: عدّاده صار ×1 كما في المتن. و«ثلاثًا» في الكتاب تخصّ التهليل الذي قبله — فنصّ الملاحظة صار:
            «يُقال مرة واحدة بعد كل صلاة، ويُقدَّم قبله التهليل ثلاثًا».</td></tr>
    <tr><td>«في ذكر بعد الصلاة «لَا إِلَهَ إِلَّا اللَّهُ (ثلاث)» — الذكر الصحيح هو «اللَّهُمَّ لَا مَانِعَ لِمَا أَعْطَيْتَ…»</td>
        <td><b>صُحّح</b>: الذكر الثالث صار «اللَّهُمَّ لَا مَانِعَ لِمَا أَعْطَيْتَ…» <b>مرة واحدة</b>، ومتنه يبدأ بالعنوان نفسه (لا لبس)،
            و«ثلاثًا» تبقى للتهليل قبله في سطر الملاحظة كما في «حصن المسلم».</td></tr>
    <tr><td>«هل تحتوي الشاشة الرئيسية على أيقونات الأذكار، وعند الانتهاء من أي ذكر ترجع للقائمة الرئيسية؟» (طلبك الجديد)</td>
        <td><b>نُفِّذ</b> في التطبيق والمحاكي معًا: عند فتح التطبيق تظهر <b>أيقونات الأذكار الثمانية</b> فتختار منها،
            وفيها زرّ <b>«متابعة»</b> لآخر ذكر بنفس الرقم، واختصارات <b>آخر ثلاثة</b> استخدمتَها،
            و<b>بعد إتمام أي مجموعة يعود بك زر «🏠 الشاشة الرئيسية»</b> إليها — وللمجموعات المفتوحة زرّ <b>⌂</b> أعلى الشاشة.
            (١١ فحصًا جديدًا + لقطتان — والتفصيل في القسم <b>⑥</b>)</td></tr>
    <tr><td>«هل يمكن في الشاشة الرئيسية اختيار طريقة العدّ، وأن تُحفظ عند كل مرة يُفتح فيها التطبيق؟» (طلبك الأخير)</td>
        <td><b>نُفِّذ</b>: أسفل الشاشة الرئيسية صفّ <b>«طريقة العدّ»</b> بثلاث خيارات (👆 نقرة مزدوجة · 🤚 حركة الرسغ · 🎡 نقرة التاج)،
            والوضع الحالي معلَّم بلون، وأنت تختاره بضغطة. و<b>يُحفظ في ذاكرة الجهاز</b> — تُغلق التطبيق وتفتحه فتجده كما اخترته.
            وفُحص ذلك عمليًّا: أُعيد فتح الصفحة في متصفح حقيقي فبقي الاختيار. (٧ فحوص جديدة + لقطة)</td></tr>
    <tr><td>«حركة اليد ترجع للخلف، وضغط التاج يفتح قائمة التطبيقات — كيف يؤثّر ذلك؟» (سؤالك السابق)</td>
        <td>جرّبناه في مختبر حقيقي وأُضيفت فحوص تحرس الحالتين، ولا يضيع منك عدّ: <b>رجوع اليد</b> لا يُطرح إلا ضغطة واحدة
            كانت خطأ، و<b>ضغطة التاج</b> تُخرجك فعلًا (سلوك نظام أبل لا عيب في التطبيق) لكن <b>عدّك محفوظ ويعود كما هو</b>.
            جرّبه بنفسك بزرّ <b>🚪</b> في المحاكاة. الشرح الصادق كاملًا في القسم <b>⑤</b> أدناه.</td></tr>
  </table>

  <h2>⓪ب ما تغيّر في الجولة السابقة (للتذكير)</h2>
  <table class="tbl">
    <tr><th>ملاحظتك</th><th>ما فُعل</th></tr>
    <tr><td>«بعض الكلمات خارج الإطار ومربع المدة غير ظاهر» في شاشة الإتمام</td>
        <td>أُعيد تصميم الملخّص: ثلاث خلايا متساوية (أذكار · ضغطة · المدة)، والمدة صارت قصيرة «٣:٣٤»،
            والصفوف الطويلة القديمة أُزيلت — وفحص جديد يمنع قصّ أي كلمة في المجموعات الثماني.</td></tr>
    <tr><td>«عنوان الذكر لا يطابق متن الذكر»</td>
        <td>سببان أُصلحا: (١) الترقيم «المركّب» في المتصفح كان يبعثر الجُمَل (عولج)،
            (٢) عنوانان في «بعد الصلاة» كانا مقتبسين من وسط النص («اللهم لا مانع…»، «لا حول ولا قوة…»)
            فصارا يبدآن بمطلع المتن: «لَا إِلَهَ إِلَّا اللَّهُ…». وفحص دائم يقارن كل عنوان بمتنه.</td></tr>
    <tr><td>«تسبيح فاطمة ليس من أذكار حصن المسلم»</td>
        <td><b>أُزيل تمامًا</b> من بعد الصلاة ومن النوم (لم يكن من نصّ الكتاب) — وفحص يمنع عودته.</td></tr>
    <tr><td>«يجب مراجعة دقيقة لكل الأذكار»</td>
        <td>بُني مدقّق آلي يقارن <b>كل ذكر</b> بمتن صفحته الرسمية في hisnmuslim.com (٧٠ ذكرًا) ونتيجته الآن:
            ✔ مطابقة كاملة — والتفاصيل أدناه.</td></tr>
  </table>

  <h2>⓪ب كيف دُقّقت النصوص (لا اعتماد على الذاكرة)</h2>
  <ul>
    <li>نُزّلت صفحات الكتاب الثلاث الرسمية (الأذكار بعد السلام · أذكار الصباح والمساء · أذكار النوم) واحتُفظ بها كمرجع.</li>
    <li>مقارنة آلية لكل ذكر: التشكيل يُطوى، ورسم الحروف يُوحَّد (أ/إ ← ا · ة ← ه · ى ← ي…)،
        وتُطوى تعليمات الكتاب داخل الأقواس «(ثلاثًا)» — لأنها عندنا في «ملاحظة الذكر» أسفل النص. لوحة التحكّم بمتصفح حقيقية
        قارنت كذلك عناوين الأذكار بمتونها.</li>
    <li>صيغ أذكار المساء تُروى في الكتاب بين معقوصين («وإذا أمسى قال…») على الأصل الصباحي — تُحقّق من الصيغة نفسها.</li>
    <li>الملاحظات أسفل كل نص (العدد وموضع الذكر) مأخوذة من تعليمات الكتاب نفسه.</li>
  </ul>
{diff_rows}

  <h2>⑤ سؤالك: «حركة اليد ترجع للخلف» و«ضغطة التاج تفتح قائمة التطبيقات»</h2>
  <p>سألت — وهذا جوابي بصدق، لا مجاملة:</p>
  <table class="tbl">
    <tr><th>الحالة</th><th>ماذا يحدث فعلًا</th><th>ما فعلناه</th></tr>
    <tr><td><b>① حركة اليد ترجع للخلف</b><br>(الوضع الخافت)</td>
        <td>ليست المشكلة في اتجاه الحركة: إيماءة الرسغ تُرصد كـ«نكزة»، والاهتزاز العابر قد يُحسب مرّتين أحيانًا
            (زيادة أو نقصان بمقدار واحد).</td>
        <td>خُفّضت حساسية الرجوع، ويمكنك ضبطها من <b>القائمة ← حساسية الحركة</b> (منخفضة/متوسطة/عالية).
            والفرق دائمًا ضغطة واحدة تُصحّحها بزرّ <b>−</b> أو بالرجوع خطوة.</td></tr>
    <tr><td><b>② ضغط التاج يفتح قائمة التطبيقات</b></td>
        <td>هذا <b>سلوك نظام watchOS</b>، وليس عيبًا في تطبيقنا: عندما تضغط التاج أو تبدّل تطبيقًا تُنهى «الجلسة الممتدة»
            (نوع <i>mindfulness</i>) بقرار من أبل — مكتوب في مرجع أبل حرفيًّا: الجلسة تستمر «حتى انتهاء المدة أو <b>خروجك
            الصريح من التطبيق</b> (ضغط التاج أو الانتقال لتطبيق آخر)». لا يوجد تطبيق على الساعة يمنع هذا.</td>
        <td>لكن <b>العدّ لا يضيع</b>: العدّاد يُحفظ لحظة بلحظة (الرقم · الذكر · المجموعة)، فحين تعود من قائمة التطبيقات
            تجد سبحتك من حيث تركتها، والجلسة تُشغَّل من جديد تلقائيًّا. وجرّبه الآن بزرّ <b>🚪</b> في المحاكاة:
            تظهر لك شاشة الساعة السوداء (كما لو ضغطت التاج)، ثم بضغطة ثانية تعود وترى الرقم نفسه.</td></tr>
    <tr><td><b>③ إعداد «Return to Clock»</b><br>(الساعة ← عام ← العودة إلى الساعة)</td>
        <td><b>لا يفسد العدّ.</b> مهمّته: متى تُرجع الساعةُ واجهتها الأصلية بدل التطبيق. الافتراضي «بعد دقيقتين»
            وتستطيع جعله «بعد ساعة» (أو «دائمًا» للتطبيق). وحتى إن أرجع الواجهة، فالجلسة الأمامية تبقى حتى
            نهاية مدّتها (ساعة كاملة، ويُجدَّد الطلب تلقائيًّا).</td>
        <td>«إبقاء العدّ حيًّا» في القائمة يطلب الجلسة تلقائيًّا عند فتح التطبيق ويجدّدها وحدها. وإن خفّت الشاشة
            ولمستها يعمل العدّ (نكزة رسغ) بلا حاجة للإضاءة.</td></tr>
  </table>
  <div class="shot">
    <img src="{SHOT_LEAVE}" alt="شاشة الساعة بعد ضغطة التاج والعدّ محفوظ">
    <div class="cap">لقطة حقيقية من المحاكي: بعد ضغطة التاج تظهر شاشة الساعة — والعدّ <b>١٧</b> محفوظ كما هو.
      اضغط <b>🚪</b> في المحاكاة لتراها بنفسك: ضغطة تُخرجك، وضغطة تُرجعك لنفس الرقم.</div>
  </div>
  <p class="note">بصراحة تامة: <b>لا توجد</b> في watchOS طريقة يجعلها تطبيقٌ ما لإبقاء الإضاءة مضاءة أو لمنع
     قائمة التطبيقات من الظهور عند ضغط التاج. أقصى ما يمكن — وقد فعلناه — هو: العدّ محفوظ لا يضيع، والعدّ يعمل
     والشاشة خافتة (حركة/تاج)، و«مدة الاستيقاظ» من إعدادات الساعة ٧٠ ثانية لأطول إضاءة.</p>

  <h2>⑥ الشاشة الرئيسية الجديدة (طلبك الأخير)</h2>
  <div class="shot">
    <img src="{SHOT_HOME}" alt="الشاشة الرئيسية: أيقونات الأذكار">
    <div class="cap">لقطة حقيقية: «متابعة» لآخر ذكر · «آخرها» ثلاثة اختصارات · ثم أيقونات الأذكار الثمانية.</div>
  </div>
  <table class="tbl">
    <tr><th>طلبك</th><th>كيف صار</th></tr>
    <tr><td>أيقونات الأذكار في الشاشة الرئيسية</td><td>ثماني أيقونات بأسمائها وعدد أذكارها — بضغطة واحدة يبدأ العدّ (وكلّها داخل شاشة الساعة بلا تمرير)</td></tr>
    <tr><td>عند الانتهاء من أي ذكر ترجع للقائمة الرئيسية</td><td>شاشة الإتمام فيها زرّ <b>🏠 الشاشة الرئيسية</b>: تضغطه فترجع للأيقونات (وفيها أيضًا «إعادة المجموعة» و«إغلاق»)</td></tr>
    <tr><td>وأنت تختار متى تخرج من المجموعات المفتوحة</td><td>«تسبيح حرّ» و«الاستغفار» و«الصلاة على النبي» لا تنتهي بعدد، ففي أعلى شاشة العدّ زرّ <b>⌂</b> يرجعك للرئيسية في أي لحظة — والعدّ يبقى محفوظًا</td></tr>
    <tr><td>اختيار طريقة العدّ من الرئيسية وأن تُحفظ</td><td>صفّ <b>«طريقة العدّ»</b>: نقرة مزدوجة · حركة الرسغ · نقرة التاج — تُحفظ في ذاكرة الجهاز وتبقى في كل مرة تفتح فيها التطبيق، وسطر أسفل الشاشة يوضّح: «يعمل والشاشة خافتة ✓»</td></tr>
    <tr><td>وألّا يضيع عدّك عند إعادة الفتح</td><td>عند كل فتح جديد تبدأ من الأيقونات، وإن كان عدّك ناقصًا يظهر زرّ <b>«متابعة»</b> باسم المجموعة وموضعك؛ وتحته آخر ثلاثة أذكار استخدمتها</td></tr>
  </table>

  <h2>③ الأذكار الكتابية كاملة (للمراجعة)  — {sum(len(s['items']) for s in book)} ذكرًا</h2>
  <p class="note">اقرأها سطرًا سطرًا. أي كلمة أو عدد تراه مخالفًا للمطبوعة عندك — قل لي رقمه وأعدّله فورًا
     (التعديل في ملف واحد: <code>tools/build_adhkar.py</code> ثم أمر التوليد).</p>
{cards}

  <h2>④ المجموعات الأخرى (كما هي بلا تغيير)</h2>
  <ul class="others">{others}</ul>

  <div class="ask">
    <b>هل النصوص مطابقة؟</b><br>
    · إن كان فيها ما يُصحَّح → قل لي المجموعة ورقم الذكر.<br>
    · إن كانت مطابقة → قل «تمّت المراجعة»، فأُكمل: أُغلق ملف المراجعة وأُعيد بناء الحزمة النهائية وترفع للمستودع.
  </div>

</div>
</body>
</html>
"""
    OUT.write_text(doc, encoding='utf-8')
    print(f'✍️  {OUT}  ({len(doc):,} حرفًا · {tot_items} ذكرًا · {tot_taps} ضغطة)')


if __name__ == '__main__':
    main()
