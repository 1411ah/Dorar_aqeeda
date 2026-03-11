# dorar-aqeeda

استخراج موسوعة العقيدة من dorar.net إلى EPUB + Markdown

## الملفات
| الملف | الوظيفة |
|---|---|
| `explore_aqeeda.py` | استكشاف هيكل الموقع |
| `dorar_aqeeda_export.py` | الاستخراج الكامل (يُضاف بعد الاستكشاف) |

## التشغيل على GitHub Actions
1. افتح تبويب **Actions**
2. اختر **Explore Aqeeda**
3. اضغط **Run workflow**
4. بعد الانتهاء: حمّل `explore-results` من **Artifacts**

## التشغيل المحلي
```bash
pip install -r requirements.txt
python explore_aqeeda.py
---

## هيكل الريبو النهائي الآن:
dorar-aqeeda/
├── .github/
│   └── workflows/
│       └── explore.yml
├── explore_aqeeda.py
├── requirements.txt
└── README.md
---

**الخطوات بعد الإنشاء:**
```bash
git init
git add .
git commit -m "init: explore script"
git remote add origin https://github.com/USERNAME/dorar-aqeeda.git
git push -u origin main
