#!/usr/bin/env python3
"""
Download all product images from giftpalacebd.com CDN
Organized into folders by category → Desktop/Prokritee_Images/<category>/
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
PRODUCTS_JSON = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json')

DESKTOP = os.path.join(os.path.expanduser('~'), 'Desktop')
OUTPUT_DIR = os.path.join(DESKTOP, 'Prokritee_Images')

# Human-readable folder names for each category id
CATEGORY_NAMES = {
    'crests-awards':        '01_Crests_Metal_Plates_Awards',
    'gift-boxes':           '02_Corporate_Gift_Boxes_Combos',
    'pins-accessories':     '03_Coat_Pins_Cufflinks_Medals',
    'smart-drinkware':      '04_Smart_Flasks_Drinkware',
    'desktop-organizers':   '05_Desktop_Organizers_Table',
    'op-pens':              '06_Premium_Pens_Diaries',
    'keyrings-accessories': '07_Keyrings_Accessories',
    'trophy-awards':        '08_Trophy_Awards',
    'italian-frames':       '09_Italian_Frames_Photo',
    'eco-bags':             '10_Eco_Jute_Bags',
    'door-plates-signage':  '11_Door_Plates_Signage',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.giftpalacebd.com/',
}

# ── Load products ──────────────────────────────────────────────────────────────
with open(PRODUCTS_JSON, 'r', encoding='utf-8') as f:
    products = json.load(f)

print(f"\n{'='*65}")
print("📦  Prokritee — Image Downloader")
print(f"{'='*65}")
print(f"  Products loaded : {len(products)}")
print(f"  Output folder   : {OUTPUT_DIR}")
print(f"{'='*65}\n")

# ── Group by section ──────────────────────────────────────────────────────────
by_section = defaultdict(list)
for p in products:
    section = p.get('section', 'unknown')
    image_url = p.get('image', '').strip()
    if image_url and 'giftpalacebd.com' in image_url:
        by_section[section].append({
            'url': image_url,
            'code': p.get('code', f"id_{p.get('id','')}"),
            'name': p.get('nameEn') or p.get('nameBn', ''),
        })

# Deduplicate URLs within each section
for section in by_section:
    seen_urls = set()
    deduped = []
    for item in by_section[section]:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            deduped.append(item)
    by_section[section] = deduped

total_images = sum(len(v) for v in by_section.values())
print(f"  Unique images to download: {total_images}\n")

# ── Summary of what will be downloaded ────────────────────────────────────────
for section, items in sorted(by_section.items()):
    folder_name = CATEGORY_NAMES.get(section, section)
    print(f"  📁  {folder_name}  ({len(items)} images)")

print()

# ── Create output folders ─────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
for section in by_section:
    folder_name = CATEGORY_NAMES.get(section, section)
    os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)

# ── Download ──────────────────────────────────────────────────────────────────
def download_file(url, dest_path, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(dest_path, 'wb') as f:
                f.write(data)
            return True, len(data)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return False, f"HTTP {e.code}"
            time.sleep(1)
        except Exception as e:
            if attempt == retries - 1:
                return False, str(e)
            time.sleep(1)
    return False, "Max retries exceeded"

downloaded = 0
failed = 0
skipped = 0
fail_log = []

grand_total = total_images
done = 0

for section, items in sorted(by_section.items()):
    folder_name = CATEGORY_NAMES.get(section, section)
    folder_path = os.path.join(OUTPUT_DIR, folder_name)
    
    print(f"\n📁  {folder_name}")
    print(f"    Downloading {len(items)} images...")
    
    cat_ok = 0
    for i, item in enumerate(items, 1):
        url = item['url']
        # Get filename from URL
        filename = url.split('/')[-1]
        dest_path = os.path.join(folder_path, filename)
        
        done += 1
        progress = f"[{done}/{grand_total}]"
        
        # Skip if already downloaded
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500:
            skipped += 1
            cat_ok += 1
            print(f"    {progress} ⏭  {filename[:40]}  (already exists)")
            continue
        
        ok, result = download_file(url, dest_path)
        if ok:
            downloaded += 1
            cat_ok += 1
            size_kb = result / 1024
            print(f"    {progress} ✅  {filename[:40]}  ({size_kb:.0f} KB)")
        else:
            failed += 1
            fail_log.append({'url': url, 'section': section, 'error': result})
            print(f"    {progress} ❌  {filename[:40]}  → {result}")
        
        # Small delay to be polite to their server
        time.sleep(0.3)
    
    print(f"    ✔  Category done: {cat_ok}/{len(items)} images")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print("📊  Download Summary")
print(f"{'='*65}")
print(f"  ✅  Downloaded : {downloaded}")
print(f"  ⏭   Skipped    : {skipped}  (already existed)")
print(f"  ❌  Failed     : {failed}")
print(f"  📁  Saved to   : {OUTPUT_DIR}")
print(f"{'='*65}")

if fail_log:
    fail_path = os.path.join(OUTPUT_DIR, 'failed_downloads.json')
    with open(fail_path, 'w', encoding='utf-8') as f:
        json.dump(fail_log, f, indent=2, ensure_ascii=False)
    print(f"\n  Failed URLs saved to: {fail_path}")

print("\n🎉  Done! Open 'Prokritee_Images' folder on your Desktop.\n")
