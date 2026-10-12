#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
#  📦 بناء حزمة التسليم TasbihWatch.zip
# ════════════════════════════════════════════════════════════════════════
#  لماذا؟ الحزمة هي ما يُرفَع إلى GitHub (المستودع المحلي منفصل متعمَّد).
#  ماذا تفعل:
#    ① تنسخ المشروع إلى مجلد مؤقّت (بلا node_modules ولا ملفات مؤقتة)
#    ② تُنشئ مستودع Git نظيفًا هناك + كوميت واحد برسالة التسليم
#    ③ تضغط الناتج إلى /home/user/TasbihWatch.zip (شاملًا .git)
#
#  الاستخدام:   bash tools/make_zip.sh "رسالة الكوميت"
# ════════════════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."
MSG="${1:-حزمة سبحة}"
TMP="$(mktemp -d)"
OUT="/home/user/TasbihWatch.zip"

mkdir -p "$TMP/TasbihWatch"
# tar بدل rsync (متوفر في كل بيئة): يستثني node_modules والمؤقتات وملفات npm الزائدة في الجذر
tar -cf - --exclude='./node_modules' --exclude='./tests/node_modules' --exclude='./.git' \
        --exclude='./package.json' --exclude='./package-lock.json' --exclude='*.tar.gz' \
        --exclude='.DS_Store' ./ | tar -xf - -C "$TMP/TasbihWatch"

cd "$TMP/TasbihWatch"
git init -q
git config user.email "mg.shuaib@gmail.com"
git config user.name "Mohammed Bashuaib"
git add -A
git commit -qm "$MSG"
echo "الكوميت: $(git rev-parse --short HEAD) · الملفات: $(git ls-files | wc -l)"
git status --porcelain | head -3

cd "$TMP"
rm -f "$OUT"
zip -qr "$OUT" TasbihWatch
echo "📦 $(du -h "$OUT" | cut -f1) → $OUT"
cd /; rm -rf "$TMP"
