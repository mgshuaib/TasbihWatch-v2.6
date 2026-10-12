#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
#  سبحة — تشغيل كل الفحوصات قبل كل تسليم
# ════════════════════════════════════════════════════════════════════════
#  الاستخدام:
#      cd tests
#      npm install puppeteer jsdom        # مرة واحدة
#      bash run-all.sh
#
#  على لينكس قد تحتاج مكتبات المتصفح:
#      sudo apt-get install -y libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
#        libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
#        libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
#        fonts-hosny-amiri fonts-noto-core fonts-noto-color-emoji
#
#  ⚠️ ملاحظة: واجهات أبل (SwiftUI/WidgetKit) لا تُترجم إلا على Mac، فتلك
#     الترجمة الحقيقية تحدث في GitHub Actions. أما هنا فنفحص الصياغة بالمترجم
#     الرسمي إن وُجد (swift-syntax-check.sh)، ونتحقق نصيًا من الواجهات والأذكار.
# ════════════════════════════════════════════════════════════════════════
set -u
cd "$(dirname "$0")"
FAIL=0

echo "════════════════════════════════════════════════════════"
echo "  ⚡ الفحص السريع (تفاعل + منطق · بلا متصفح)"
echo "════════════════════════════════════════════════════════"
if [ -d node_modules/jsdom ]; then
  node jsdom-suite.mjs || FAIL=1
else
  echo "  ⚠ jsdom غير مثبّت — نفّذ: npm install jsdom"
fi

echo
echo "════════════════════════════════════════════════════════"
echo "  🖥️  الفحص البصري (تخطيط حقيقي · متصفح Chromium)"
echo "════════════════════════════════════════════════════════"
if [ -d node_modules/puppeteer ]; then
  node browser-suite.mjs || FAIL=1
else
  echo "  ⚠ puppeteer غير مثبّت — نفّذ: npm install puppeteer"
fi

echo
echo "════════════════════════════════════════════════════════"
echo "  🔬 تدقيق كل نصّ ذكر مقابل صفحات الكتاب الرسمية (hisnmuslim.com)"
echo "════════════════════════════════════════════════════════"
if [ -f ../../.sources/page25.html ]; then        # صفحات الكتاب الرسمية (خارج المشروع — لا تُرفع مع الكود)
  python3 ../tools/audit_adhkar.py || FAIL=1
else
  echo "  ℹ️ صفحات المصدر غير منزَّلة في ../../.sources — تخطّي تدقيق النصوص"
  echo "     التنزيل:  mkdir -p ../../.sources && cd ../../.sources && for n in 25 1 0; do curl -sL \"https://hisnmuslim.com/i/ar/\$n\" -o page\$n.html; done"
fi

echo
echo "════════════════════════════════════════════════════════"
echo "  🧩 صياغة Swift بالمترجم الرسمي (يكشف الفاصلة الناقصة وأمثالها)"
echo "════════════════════════════════════════════════════════"
bash swift-syntax-check.sh || FAIL=1

echo
echo "════════════════════════════════════════════════════════"
echo "  🧭 فحص Swift (واجهات + تطابق نصوص الأذكار + مراجع النماذج)"
echo "════════════════════════════════════════════════════════"
python3 swift-api-check.py || FAIL=1

echo
echo "════════════════════════════════════════════════════════"
echo "  ⚙️  فحص سير عمل GitHub Actions (قبل الدفع)"
echo "════════════════════════════════════════════════════════"
python3 workflow-check.py || FAIL=1

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✅ كل الفحوصات سليمة"
else
  echo "❌ توجد فحوصات فاشلة — راجع النتائج أعلاه"
fi
exit "$FAIL"
