#!/usr/bin/env python3
"""
explore_aqeeda.py — استكشاف هيكل dorar.net/aqeeda قبل الاستخراج الكامل
الناتج: تقرير في explore_report.txt + عينات HTML في explore_samples/

Usage:
    python explore_aqeeda.py
    SAMPLE=20 python explore_aqeeda.py   # استكشاف أعمق
"""

import os
import re
import time
import json
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
START_URL  = "https://dorar.net/aqeeda"
BASE_URL   = "https://dorar.net"
PAGE_RE    = re.compile(r"/aqeeda/(\d+)")
DELAY      = 0.6
TIMEOUT    = 20
SAMPLE_N   = int(os.getenv("SAMPLE", 15))   # عدد صفحات العينة
OUT_DIR    = Path("explore_samples")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
}

_session = requests.Session()
_session.headers.update(HEADERS)

# ── HTTP ──────────────────────────────────────────────────────────────────────
def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = _session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None

# ── أدوات الطباعة ─────────────────────────────────────────────────────────────
def section(title: str, width: int = 70) -> str:
    bar = "─" * width
    return f"\n{bar}\n  {title}\n{bar}"

# ─────────────────────────────────────────────────────────────────────────────
# 1. فحص الصفحة الرئيسية
# ─────────────────────────────────────────────────────────────────────────────
def explore_index(report: list[str]) -> list[int]:
    report.append(section("1. الصفحة الرئيسية — dorar.net/aqeeda"))
    soup = fetch(START_URL)
    if not soup:
        report.append("  [فشل] لم يمكن جلب الصفحة الرئيسية")
        return []

    # ── حفظ HTML الرئيسي ──
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(str(soup), encoding="utf-8")
    report.append(f"  HTML محفوظ في: explore_samples/index.html")

    # ── عنوان الصفحة ──
    title = soup.find("title")
    report.append(f"  <title>: {title.get_text(strip=True) if title else '—'}")

    # ── جمع كل روابط /aqeeda/N ──
    ids: set[int] = set()
    for a in soup.find_all("a", href=True):
        m = PAGE_RE.search(a["href"])
        if m:
            ids.add(int(m.group(1)))

    sorted_ids = sorted(ids)
    report.append(f"\n  روابط /aqeeda/N في الصفحة الرئيسية: {len(sorted_ids)}")
    if sorted_ids:
        report.append(f"  أصغر ID: {sorted_ids[0]}  |  أكبر ID: {sorted_ids[-1]}")
        report.append(f"  أول 20 ID: {sorted_ids[:20]}")

    # ── بنية الروابط (أنماط مختلفة) ──
    report.append("\n  أنماط الروابط الموجودة (غير /aqeeda/N):")
    other_patterns: Counter = Counter()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/aqeeda" in href and not PAGE_RE.search(href):
            other_patterns[href.split("?")[0]] += 1
    for pat, cnt in other_patterns.most_common(15):
        report.append(f"    {cnt:>3}x  {pat}")

    # ── div/section رئيسية ──
    report.append("\n  الـ divs الرئيسية (id أو class بارزة):")
    for tag in soup.find_all(True, id=True):
        report.append(f"    <{tag.name} id='{tag['id']}'>")
    for tag in soup.find_all(["nav", "main", "article", "section"]):
        cls = " ".join(tag.get("class", []))
        report.append(f"    <{tag.name} class='{cls[:60]}'>")

    # ── هل هناك رابط /refs/aqeeda ؟ ──
    refs_links = [a["href"] for a in soup.find_all("a", href=True) if "refs" in a["href"]]
    report.append(f"\n  روابط /refs/: {refs_links[:5] if refs_links else 'لا يوجد'}")

    # ── هل هناك article خاص بالمنهج؟ ──
    article_links = [a["href"] for a in soup.find_all("a", href=True) if "/article/" in a["href"]]
    report.append(f"  روابط /article/: {article_links[:5] if article_links else 'لا يوجد'}")

    return sorted_ids


# ─────────────────────────────────────────────────────────────────────────────
# 2. فحص صفحة محتوى واحدة بعمق
# ─────────────────────────────────────────────────────────────────────────────
def explore_page_deep(url: str, label: str, report: list[str]) -> BeautifulSoup | None:
    report.append(f"\n  [{label}] {url}")
    soup = fetch(url)
    if not soup:
        report.append("    [فشل]")
        return None

    # حفظ HTML
    safe = label.replace("/", "_").replace(":", "")
    (OUT_DIR / f"{safe}.html").write_text(str(soup), encoding="utf-8")

    # عنوان h1
    h1 = soup.find("h1", class_="h5-responsive") or soup.find("h1")
    report.append(f"    h1: {h1.get_text(strip=True) if h1 else '—'}")

    # breadcrumb
    bc = soup.find("ol", class_="breadcrumb")
    if bc:
        crumbs = [li.get_text(strip=True) for li in bc.find_all("li")]
        report.append(f"    breadcrumb ({len(crumbs)}): {' > '.join(crumbs)}")
    else:
        report.append("    breadcrumb: لا يوجد")

    # #cntnt
    cntnt = soup.find("div", id="cntnt")
    report.append(f"    #cntnt: {'موجود' if cntnt else 'غائب'}")
    if cntnt:
        # أبناء مباشرون
        direct = [c for c in cntnt.children if hasattr(c, "name") and c.name]
        report.append(f"    أبناء #cntnt: {[(c.name, ' '.join(c.get('class',[])))  for c in direct[:8]]}")

        # w-100 mt-4
        body_div = cntnt.find("div", class_=lambda c: c and "w-100" in c and "mt-4" in c)
        report.append(f"    div.w-100.mt-4: {'موجود' if body_div else 'غائب'}")

    # span classes
    span_classes: Counter = Counter()
    for span in (cntnt or soup).find_all("span"):
        for cls in span.get("class", []):
            span_classes[cls] += 1
    report.append(f"    span classes: {dict(span_classes.most_common(10))}")

    # زر التالي/السابق
    nav_texts = []
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        if t in ("التالي", "السابق", "Next", "Prev"):
            nav_texts.append(f"{t} → {a['href']}")
    report.append(f"    روابط تنقل: {nav_texts if nav_texts else 'لا يوجد'}")

    # هل هناك هوامش (tip)؟
    tips = (cntnt or soup).find_all("span", class_="tip")
    report.append(f"    هوامش .tip: {len(tips)}")

    # عدد الفقرات والعناوين
    tags_count = Counter()
    for t in ["p", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table"]:
        n = len((cntnt or soup).find_all(t))
        if n:
            tags_count[t] = n
    report.append(f"    العناصر: {dict(tags_count)}")

    return soup


# ─────────────────────────────────────────────────────────────────────────────
# 3. عينة من الصفحات — رصد أنماط breadcrumb والمستويات
# ─────────────────────────────────────────────────────────────────────────────
def explore_sample_pages(sorted_ids: list[int], report: list[str]) -> None:
    report.append(section("3. عينة من صفحات الموسوعة"))

    # اختر صفحات موزعة: أول + وسط + آخر
    n = len(sorted_ids)
    if n == 0:
        report.append("  لا توجد صفحات للاستكشاف")
        return

    indices = sorted(set([
        0, 1, 2,
        n // 4, n // 2, 3 * n // 4,
        max(0, n - 3), max(0, n - 2), n - 1,
        *range(min(SAMPLE_N, n))
    ]))
    sample_ids = [sorted_ids[i] for i in indices if i < n]

    bc_depth_counter: Counter = Counter()
    level_patterns: list[str] = []
    next_url_found = False
    first_next = None

    for pid in sample_ids[:SAMPLE_N]:
        url  = f"{BASE_URL}/aqeeda/{pid}"
        soup = fetch(url)
        if not soup:
            continue
        time.sleep(DELAY)

        h1 = soup.find("h1", class_="h5-responsive") or soup.find("h1")
        bc = soup.find("ol", class_="breadcrumb")
        crumbs = [li.get_text(strip=True) for li in bc.find_all("li")] if bc else []
        bc_depth_counter[len(crumbs)] += 1

        h1_txt = h1.get_text(strip=True) if h1 else "—"
        level_patterns.append(f"    ID={pid:>5} | crumbs={len(crumbs)} | {' > '.join(crumbs[-3:])}")

        # أول رابط "التالي"
        if not next_url_found:
            for a in soup.find_all("a", href=True):
                if a.get_text(strip=True) == "التالي":
                    first_next = urljoin(url, a["href"])
                    next_url_found = True
                    break

        print(f"  explored ID={pid}: {h1_txt[:50]}")

    report.append(f"\n  توزيع عمق breadcrumb: {dict(bc_depth_counter)}")
    report.append(f"\n  عينة صفحات:")
    report.extend(level_patterns)

    if first_next:
        report.append(f"\n  أول رابط 'التالي' وجدناه: {first_next}")
    else:
        report.append("\n  لم يُعثر على رابط 'التالي' — قد يكون التنقل مختلفاً")


# ─────────────────────────────────────────────────────────────────────────────
# 4. تتبع سلسلة التنقل بالتالي/السابق
# ─────────────────────────────────────────────────────────────────────────────
def explore_navigation_chain(start_id: int, steps: int, report: list[str]) -> None:
    report.append(section("4. تتبع سلسلة التنقل (التالي)"))
    url   = f"{BASE_URL}/aqeeda/{start_id}"
    chain = [url]

    for _ in range(steps):
        soup = fetch(url)
        if not soup:
            break
        time.sleep(DELAY)
        nxt = None
        for a in soup.find_all("a", href=True):
            if PAGE_RE.search(a["href"]) and a.get_text(strip=True) == "التالي":
                nxt = urljoin(url, a["href"])
                break
        if not nxt or nxt in chain:
            break
        chain.append(nxt)
        url = nxt

    report.append(f"  سلسلة مكتشفة ({len(chain)} صفحة):")
    for u in chain:
        report.append(f"    {u}")

    # هل الـ IDs متتالية أم تقفز؟
    ids = [int(PAGE_RE.search(u).group(1)) for u in chain if PAGE_RE.search(u)]
    if len(ids) > 1:
        diffs = [ids[i+1] - ids[i] for i in range(len(ids)-1)]
        report.append(f"\n  فروقات IDs: {diffs}")
        report.append(f"  التنقل {'متتالي رقمياً' if all(d==1 for d in diffs) else 'يقفز — ليس رقمياً متتالياً'}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. فحص صفحة متعددة المستويات (عينة عميقة)
# ─────────────────────────────────────────────────────────────────────────────
def explore_deep_pages(sorted_ids: list[int], report: list[str]) -> None:
    report.append(section("5. فحص عميق لـ 3 صفحات نموذجية"))
    # أخذ صفحة من البداية والوسط والنهاية
    samples = [sorted_ids[0]]
    if len(sorted_ids) > 2:
        samples.append(sorted_ids[len(sorted_ids)//2])
        samples.append(sorted_ids[-1])

    for pid in samples:
        url = f"{BASE_URL}/aqeeda/{pid}"
        explore_page_deep(url, f"page_{pid}", report)
        time.sleep(DELAY)


# ─────────────────────────────────────────────────────────────────────────────
# 6. روابط خاصة محتملة (refs, article)
# ─────────────────────────────────────────────────────────────────────────────
def explore_special_urls(report: list[str]) -> None:
    report.append(section("6. الصفحات الخاصة المحتملة"))
    candidates = [
        ("https://dorar.net/refs/aqeeda",   "refs"),
        ("https://dorar.net/article/2112",   "article_2112"),
        ("https://dorar.net/article/1",      "article_1"),
    ]
    for url, label in candidates:
        r = _session.get(url, timeout=TIMEOUT)
        status = r.status_code
        report.append(f"  {url}  →  HTTP {status}")
        if status == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            (OUT_DIR / f"special_{label}.html").write_text(str(soup), encoding="utf-8")
            h1 = soup.find("h1")
            report.append(f"    h1: {h1.get_text(strip=True) if h1 else '—'}")
        time.sleep(DELAY)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    report: list[str] = [
        "=" * 70,
        "  تقرير استكشاف dorar.net/aqeeda",
        "=" * 70,
        f"  SAMPLE={SAMPLE_N}",
    ]

    print("1) فحص الصفحة الرئيسية…")
    sorted_ids = explore_index(report)

    print("\n2) فحص صفحات خاصة محتملة…")
    report.append(section("2. الصفحات الخاصة"))
    explore_special_urls(report)

    if sorted_ids:
        print(f"\n3) عينة من {SAMPLE_N} صفحة…")
        explore_sample_pages(sorted_ids, report)

        print("\n4) تتبع سلسلة التنقل (10 خطوات)…")
        explore_navigation_chain(sorted_ids[0], steps=10, report=report)

        print("\n5) فحص عميق لـ 3 صفحات…")
        explore_deep_pages(sorted_ids, report)
    else:
        report.append("\n  [تحذير] لم يُعثر على IDs — تحقق من الصفحة الرئيسية يدوياً")

    # ── حفظ التقرير ──
    report_text = "\n".join(report)
    Path("explore_report.txt").write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    print("\n✓ التقرير محفوظ في: explore_report.txt")
    print(f"✓ ملفات HTML في: {OUT_DIR}/")


if __name__ == "__main__":
    main()
