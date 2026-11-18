#!/usr/bin/env python3
"""
Import all products from prokriteebd.com into Prokritee website.
Replaces all occurrences of Prokritee with Prokritee / প্রকৃতি.
Categorizes into 11 specialized corporate gift sections.
Synchronizes data/products.json, data/sections.json, and assets/js/app.js.
"""

import os
import re
import json
import random
from html import unescape

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PAGES_DIR = "/tmp/gp_pages"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SECTIONS_FILE = os.path.join(DATA_DIR, "sections.json")

# 11 Corporate Gift Sections
ALL_SECTIONS = [
    {
        "id": "gift-boxes",
        "titleBn": "কর্পোরেট গিফট বক্স ও কম্বো প্যাকেজ",
        "titleEn": "Corporate Gift Boxes & Combos",
        "desc": "প্রতিষ্ঠানের কর্মকর্তা ও সম্মানিত ক্লায়েন্টদের জন্য প্রিমিয়াম হার্ডবক্স কম্বো সেট। কাস্টম লোগো প্রিন্ট সুবিধা সহ।",
        "descEn": "Premium hard-box combo sets for company executives and VIP clients, with custom logo printing.",
        "icon": "fa-solid fa-gift",
        "badge": "সবচেয়ে জনপ্রিয়",
        "badgeEn": "Most Popular"
    },
    {
        "id": "crests-awards",
        "titleBn": "ক্রেস্ট, মেটাল প্লেট ও ক্রিস্টাল অ্যাওয়ার্ড",
        "titleEn": "Crests, Metal Plates & Crystal Awards",
        "desc": "সম্মাননা স্মারক, ভিআইপি রিটায়ারমেন্ট ও বিশেষ অবদানের জন্য রাজকীয় মেটাল রাউন্ড প্লেট, এক্রিলিক ও ক্রিস্টাল ক্রেস্ট।",
        "descEn": "Royal metal round plates, acrylic and crystal crests for recognition awards, VIP retirement and achievements.",
        "icon": "fa-solid fa-award",
        "badge": "প্রিমিয়াম কোয়ালিটি",
        "badgeEn": "Premium Quality"
    },
    {
        "id": "smart-drinkware",
        "titleBn": "স্মার্ট ওয়াটার বোটল ও ভ্যাকুয়াম ফ্লাস্ক",
        "titleEn": "Smart Vacuum Flasks & Drinkware",
        "desc": "ডিজিটাল LED তাপমাত্রা প্রদর্শক বোতল, ফুড-গ্রেড স্টিল ফ্লাস্ক ও কাস্টমাইজড সাবলিমেশন সিরামিক মগ।",
        "descEn": "Digital LED temperature display bottles, food-grade steel flasks and customized sublimation ceramic mugs.",
        "icon": "fa-solid fa-bottle-water",
        "badge": "হট কালেকশন",
        "badgeEn": "Hot Collection"
    },
    {
        "id": "desktop-organizers",
        "titleBn": "ডেস্কটপ অর্গানাইজার ও অফিস টেবিল কালেকশন",
        "titleEn": "Desktop Organizers & Table Accessories",
        "desc": "উডেন ও লেদারেট মাল্টি-কম্পার্টমেন্ট পেন স্ট্যান্ড, বিজনেস কার্ড হোল্ডার, টেবিল ওয়াচ ও ডেস্ক অর্গানাইজার।",
        "descEn": "Wooden & leatherette multi-compartment pen stands, business card holders, table watches and desk organizers.",
        "icon": "fa-solid fa-boxes-stacked",
        "badge": "এক্সিকিউটিভ চয়েস",
        "badgeEn": "Executive Choice"
    },
    {
        "id": "op-pens",
        "titleBn": "সিগনেচার মেটাল পেন (OP সিরিজ)",
        "titleEn": "Executive Metal Pens (OP Series)",
        "desc": "স্মুথ ব্ল্যাক জেল রিফিল ও লেজার খোদাই লোগো প্রিন্ট সহ প্রিমিয়াম মেটালিক রোলার ও বলপেন কালেকশন।",
        "descEn": "Smooth black gel refills and laser-engraved logo branding with premium metallic roller and ballpoint pens.",
        "icon": "fa-solid fa-pen-nib",
        "badge": "বেস্ট সেলার",
        "badgeEn": "Best Seller"
    },
    {
        "id": "pins-accessories",
        "titleBn": "কোটপিন, কাফলিংক, টাই ক্লিপ ও মেডেল",
        "titleEn": "Coat Pins, Cufflinks & Honor Medals",
        "desc": "কোম্পানি লোগো খোদাইকৃত মেটালিক কোটপিন, গোল্ডেন/সিলভার কাফলিংক, টাই বার ও সম্মাননা মেডেল।",
        "descEn": "Company logo engraved metallic coat pins, golden/silver cufflinks, tie bars and honor medals.",
        "icon": "fa-solid fa-medal",
        "badge": "কাস্টম ডাই কাস্টিং",
        "badgeEn": "Custom Die Casting"
    },
    {
        "id": "eco-bags",
        "titleBn": "পাটজাত ও পরিবেশবান্ধব কর্পোরেট ব্যাগ",
        "titleEn": "Eco Jute & Conference Bags",
        "desc": "১০০% প্রাকৃতিক পাট ও কাপড়ে তৈরি সেমিনার ব্যাগ, ল্যাপটপ স্লিভ এবং শপিং টোট ব্যাগ।",
        "descEn": "100% natural eco-friendly jute and canvas seminar bags, laptop sleeves and corporate tote bags.",
        "icon": "fa-solid fa-leaf",
        "badge": "১০০% ইকো-ফ্রেন্ডলি",
        "badgeEn": "100% Eco-Friendly"
    },
    {
        "id": "trophy-awards",
        "titleBn": "ট্রফি, শিল্ড ও স্পোর্টস অ্যাওয়ার্ড",
        "titleEn": "Trophies, Shields & Sports Awards",
        "desc": "ক্রিকেট, ফুটবল, বার্ষিক ক্রীড়া প্রতিযোগিতা ও বিভিন্ন টুর্নামেন্টের জন্য আকর্ষণীয় চ্যাম্পিয়নশিপ ট্রফি ও শিল্ড।",
        "descEn": "Prestigious championship trophies, tournament shields and sports achievement cups.",
        "icon": "fa-solid fa-trophy",
        "badge": "চ্যাম্পিয়ন চয়েস",
        "badgeEn": "Champion Choice"
    },
    {
        "id": "italian-frames",
        "titleBn": "ইতালিয়ান ফ্রেম ও এক্সিকিউটিভ গ্লাস",
        "titleEn": "Italian Frames & Executive Eyewear",
        "desc": "স্টাইলিশ ও ক্লাসিক ডিজাইনের প্রিমিয়াম ইতালিয়ান সানগ্লাস ও ফ্যাশনেবল অপটিক্যাল ফ্রেম।",
        "descEn": "Stylish and classic designer premium Italian eyewear frames and sunglasses.",
        "icon": "fa-solid fa-glasses",
        "badge": "ইতালিয়ান কালেকশন",
        "badgeEn": "Italian Collection"
    },
    {
        "id": "keyrings-accessories",
        "titleBn": "মেটাল ও লেদার চাবির রিং",
        "titleEn": "Premium Metal & Leather Keyrings",
        "desc": "কাস্টমাইজড ব্র্যান্ড লোগো খোদাই করা মেটাল, লেদার ও উডেন প্রিমিয়াম কি-রিং কালেকশন।",
        "descEn": "Custom logo engraved metallic, leather and wooden premium keychains and promotional keyrings.",
        "icon": "fa-solid fa-key",
        "badge": "ব্র্যান্ডিং গিফট",
        "badgeEn": "Branding Gift"
    },
    {
        "id": "door-plates-signage",
        "titleBn": "ডোর প্লেট, লেকচার স্ট্যান্ড ও সাইনেজ",
        "titleEn": "Door Plates, Lecture Stands & Signage",
        "desc": "অফিস ও কনফারেন্স রুমের জন্য এক্সিকিউটিভ ডোর নেমপ্লেট, মেটাল সাইনবোর্ড ও লেকচার স্ট্যান্ড।",
        "descEn": "Executive door name plates, conference podiums, signage and lecture stands for corporate offices.",
        "icon": "fa-solid fa-chalkboard-user",
        "badge": "অফিস সল্যুশন",
        "badgeEn": "Office Solution"
    }
]

# Classification maps
PREFIX_MAP = {
    'BM': 'crests-awards',
    'CR': 'crests-awards',
    'AC': 'crests-awards',
    'MR': 'crests-awards',
    'WR': 'crests-awards',
    'WD': 'crests-awards',
    'MA': 'crests-awards',
    'CP': 'pins-accessories',
    'OP': 'op-pens',
    'GB': 'gift-boxes',
    'DW': 'smart-drinkware',
    'DO': 'desktop-organizers',
    'EB': 'eco-bags',
    'TR': 'trophy-awards',
    'ITF': 'italian-frames',
    'DP': 'door-plates-signage',
    'LS': 'door-plates-signage',
    'KR': 'keyrings-accessories',
    'UB': 'eco-bags',
    'CW': 'desktop-organizers',
    'WA': 'desktop-organizers'
}

KEYWORDS_MAP = {
    'gift-boxes': ['gift box', 'gift hamper', 'combo', 'corporate set', 'gift set', 'executive set', 'occasional gift', 'ifter box', 'womens box'],
    'crests-awards': ['crest', 'award', 'brass metal', 'wooden crest', 'acrylic', 'metal plate', 'honor board', 'honor', 'plate with wooden', 'metal round', 'paper weight', 'plate'],
    'smart-drinkware': ['flask', 'bottle', 'drinkware', 'vacuum', 'mug', 'cup', 'water bottle'],
    'desktop-organizers': ['organizer', 'desktop', 'table', 'clock', 'calendar', 'pen stand', 'table watch', 'watch', 'tissue box'],
    'op-pens': ['pen', 'metal pen', 'ballpoint', 'roller', 'fountain'],
    'pins-accessories': ['pin', 'coat pin', 'cufflink', 'medal', 'tie clip', 'badge', 'coin', 'ribbon', 'tshirt and cap'],
    'eco-bags': ['bag', 'jute', 'conference bag', 'tote', 'backpack', 'canvas', 'folder', 'umbrella'],
    'trophy-awards': ['trophy', 'cricket', 'football', 'shield', 'cup award'],
    'italian-frames': ['frame', 'eyewear', 'itf-'],
    'keyrings-accessories': ['keyring', 'key chain', 'key ring'],
    'door-plates-signage': ['door', 'name plate', 'sign', 'signage', 'lecture stand', 'podium']
}

DEFAULT_PRICES = {
    'gift-boxes': (2500, 6500),
    'crests-awards': (1200, 3800),
    'smart-drinkware': (650, 1600),
    'desktop-organizers': (750, 2200),
    'op-pens': (280, 850),
    'pins-accessories': (180, 480),
    'eco-bags': (250, 750),
    'trophy-awards': (1500, 4800),
    'italian-frames': (2200, 4500),
    'keyrings-accessories': (120, 350),
    'door-plates-signage': (1200, 3200)
}

BADGES_POOL = ["Best Seller", "Popular", "VIP Choice", "Corporate Choice", "Premium", "New Collection", "Top Rated"]

def clean_brand(text):
    if not text:
        return ''
    text = re.sub(r'(?i)gift\s*palace\s*bd', 'Prokritee', text)
    text = re.sub(r'(?i)gift\s*palace', 'Prokritee', text)
    text = re.sub(r'(?i)prokritee', 'prokritee', text)
    text = re.sub(r'গिफ्ट\s*প্যালেস', 'প্রকৃতি', text)
    # Clean redundant whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_sku(title, url, category, fallback_id):
    # Try finding exact code like BM-127, ITF-101-G, GB-183, CP-118, OP-119, MR-34
    m = re.search(r'\b([A-Z]{2,4}[-\s]?\d{1,4}(?:[-_][A-Za-z0-9]+)?)\b', title)
    if m:
        sku = m.group(1).upper().replace(' ', '-')
        if len(sku) <= 12 and not sku.startswith('HTTP'):
            return sku
    
    # Try extracting from URL slug
    slug = url.split('/')[-1]
    m_slug = re.search(r'([a-z]{2,4}-\d{1,4}(?:-[a-z0-9]+)?)', slug)
    if m_slug:
        candidate = m_slug.group(1).upper()
        if len(candidate) <= 12:
            return candidate

    # Category based fallback prefix
    cat_prefix = {
        'gift-boxes': 'GB',
        'crests-awards': 'CR',
        'smart-drinkware': 'DW',
        'desktop-organizers': 'DO',
        'op-pens': 'OP',
        'pins-accessories': 'PA',
        'eco-bags': 'EB',
        'trophy-awards': 'TR',
        'italian-frames': 'ITF',
        'keyrings-accessories': 'KR',
        'door-plates-signage': 'DP'
    }.get(category, 'PK')

    return f"{cat_prefix}-{fallback_id}"

def generate_bangla_name(code, title_en, category):
    t_clean = re.sub(r'^Model:?\s*', '', title_en, flags=re.IGNORECASE).strip()
    
    bangla_descriptors = {
        'gift-boxes': 'কর্পোরেট লাক্সারি গিফট বক্স ও কম্বো প্যাকেজ',
        'crests-awards': 'সম্মাননা স্মারক ক্রেস্ট ও মেটাল প্লেট',
        'smart-drinkware': 'স্মার্ট ভ্যাকুয়াম ফ্লাস্ক ও ওয়াটার বোটল',
        'desktop-organizers': 'এক্সিকিউটিভ ডেস্কটপ অর্গানাইজার ও টেবিল কালেকশন',
        'op-pens': 'সিগনেচার মেটাল রোলার ও বলপেন',
        'pins-accessories': 'কাস্টমাইজড মেটালিক ল্যাপেল কোটপিন ও ব্যাজ',
        'eco-bags': 'পরিবেশবান্ধব পাটজাত ও কনফারেন্স ব্যাগ',
        'trophy-awards': 'চ্যাম্পিয়নশিপ ট্রফি ও স্পোর্টস শিল্ড অ্যাওয়ার্ড',
        'italian-frames': 'প্রিমিয়াম স্টাইলিশ ইতালিয়ান ফ্রেম ও চশমা',
        'keyrings-accessories': 'কাস্টমাইজড ব্র্যান্ডেড মেটাল ও লেদার কি-রিং',
        'door-plates-signage': 'এক্সিকিউটিভ ডোর নেমপ্লেট ও মেটাল সাইনেজ'
    }

    desc = bangla_descriptors.get(category, 'কর্পোরেট গিফট ও সম্মাননা স্মারক')
    
    # If title mentions specific types, refine
    tl = title_en.lower()
    if 'acrylic' in tl:
        desc = 'প্রিমিয়াম এক্রিলিক সম্মাননা ক্রেস্ট'
    elif 'cufflink' in tl:
        desc = 'কাস্টম গোল্ডেন/সিলভার মেটাল কাফলিংক সেট'
    elif 'medal' in tl:
        desc = 'সম্মাননা মেডেল ও রিবন'
    elif 'pen' in tl:
        desc = 'সিগনেচার মেটালিক এক্সিকিউটিভ পেন'
    elif 'jute' in tl:
        desc = '১০০% প্রাকৃতিক পাটজাত কনফারেন্স ব্যাগ'
    elif 'clock' in tl or 'watch' in tl:
        desc = 'এক্সিকিউটিভ ওয়াল ও টেবিল ক্লক'
    elif 'keyring' in tl:
        desc = 'প্রিমিয়াম মেটাল ও লেদার চাবির রিং'
    elif 'flask' in tl:
        desc = 'স্মার্ট ডিজিটাল ভ্যাকুয়াম ফ্লাস্ক'

    return f"{code} {desc}"

def generate_description(name_en, category):
    base_descriptions = {
        'gift-boxes': 'প্রতিষ্ঠানের বিশেষ আয়োজন, এজিএম, বর্ষপূর্তি ও ভিআইপি ক্লায়েন্টদের জন্য প্রিমিয়াম গিফট সেট। কাস্টমাইজড লেজার লোগো প্রিন্ট এবং লাক্সারি হার্ডবক্স প্যাকেজিং সুবিধা সহ প্রকৃতি (Prokritee) এর এক্সক্লুসিভ কালেকশন।',
        'crests-awards': 'বিশেষ সম্মাননা, অবসর সংবর্ধনা ও অসাধারণ অবদানের স্বীকৃতিস্বরূপ রাজকীয় মেটাল ও ক্রিস্টাল ক্রেস্ট। নিখুঁত খোদাই এবং প্রিমিয়াম পলিশিং ফিনিশ সহ তৈরি।',
        'smart-drinkware': 'খাদ্য-উপযোগী স্টেইনলেস স্টিল ভ্যাকুয়াম ফ্লাস্ক ও পানীয় বোতল। দীর্ঘ সময় তাপমাত্রা বজায় রাখে। কর্পোরেট ক্লায়েন্টদের জন্য কালার লোগো প্রিন্ট ও গিফট বক্স সহ।',
        'desktop-organizers': 'অফিস ডেস্ক ও এক্সিকিউটিভ টেবিলের জন্য আধুনিক অর্গানাইজার। পেন হোল্ডার, ভিজিটিং কার্ড ও প্রয়োজনীয় এক্সেসরিজ রাখার সুবিন্যস্ত সমাধান।',
        'op-pens': 'মসৃণ প্রিমিয়াম জেল রিফিল ও টেকসই মেটালিক বডি। প্রতিষ্ঠানের লোগো লেজার এনগ্রেভিং সহ কর্পোরেট উপহারের জন্য চমৎকার চয়েস।',
        'pins-accessories': 'উচ্চমানের ডাই-কাস্ট মেটালিক কোটপিন ও কাফলিংক। টেকসই রঙের এনামেল কোটিং ও নিখুঁত ফিনিশিং।',
        'eco-bags': '১০০% পরিবেশবান্ধব প্রাকৃতিক পাট ও কাপড়ের কনফারেন্স ও সেমিনার ব্যাগ। মজবুত স্টিচিং এবং বড় আকারে প্রতিষ্ঠানের নাম ও লোগো স্ক্রিন প্রিন্টের ব্যবস্থা।',
        'trophy-awards': 'টুর্নামেন্ট, বার্ষিক ক্রীড়া ও বিভিন্ন প্রতিযোগিতার বিজয়ীদের জন্য আকর্ষণীয় ডিজাইনের ট্রফি ও মেডেল। গোল্ডেন ও সিলভার ফিনিশ সহ।',
        'italian-frames': 'আধুনিক ট্রেন্ডি ও প্রফেশনাল লুকের প্রিমিয়াম ইতালিয়ান সানগ্লাস ও ফ্যাশন ফ্রেম কালেকশন। আরামদায়ক ফিটিং ও দীর্ঘস্থায়ী মেটেরিয়াল।',
        'keyrings-accessories': 'প্রতিদিনের ব্যবহারে ব্র্যান্ড পরিচিতি বৃদ্ধির জন্য আদর্শ প্রমোশনাল গিফট। নিখুঁত এচিং ও মেটাল লোগো খোদাই করা।',
        'door-plates-signage': 'কর্পোরেট অফিস ও মিটিং রুমের জন্য মেটালিক ডোর প্লেট ও সাইনবোর্ড। ক্লাসিক ও প্রফেশনাল উপস্থাপনা।'
    }
    return base_descriptions.get(category, 'কর্পোরেট উপহার ও সম্মাননা স্মারকের জন্য প্রকৃতি (Prokritee) এর প্রিমিয়াম কালেকশন।')

def main():
    print("═"*65)
    print("🚀 Starting Prokritee Catalog Import for Prokritee...")
    print("═"*65)

    products = []
    seen_urls = set()
    sku_counter = {}

    for p in range(1, 37):
        path = os.path.join(PAGES_DIR, f"page_{p}.html")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        cards = re.findall(r'<div class=\"aiz-card-box.*?</div>\s*</div>\s*</div>', html, re.DOTALL)
        for c in cards:
            m_link = re.search(r'<a href=[\"\'](https://www\.prokriteebd\.com/product/[^\"\']+)[\"\'][^>]*title=[\"\']([^\"\']+)[\"\']', c)
            if not m_link:
                m_link = re.search(r'<a href=[\"\'](https://www\.prokriteebd\.com/product/[^\"\']+)[\"\']', c)
                if not m_link:
                    continue
                url = m_link.group(1)
                title_m = re.search(r'title=[\"\']([^\"\']+)[\"\']', c)
                title = title_m.group(1) if title_m else ''
            else:
                url = m_link.group(1)
                title = m_link.group(2)

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Image extraction
            img_m = re.search(r'src=[\"\'](https://www\.prokriteebd\.com/public/uploads/all/[^\"\']+\.(?:jpg|png|webp|jpeg))[\"\']', c)
            if not img_m:
                img_m = re.search(r'data-src=[\"\'](https://www\.prokriteebd\.com/public/uploads/all/[^\"\']+\.(?:jpg|png|webp|jpeg))[\"\']', c)
            img_url = img_m.group(1) if img_m else "assets/images/logo.jpg"

            # Price extraction
            price_m = re.search(r'class=[\"\'][^\"\']*text-primary[^\"\']*[\"\']>\s*৳\s*([0-9,]+(?:\.[0-9]+)?)', c)
            price_str = price_m.group(1).replace(',', '') if price_m else '0'
            try:
                price = int(float(price_str))
            except:
                price = 0

            title_clean = clean_brand(unescape(title).strip())
            if not title_clean:
                title_clean = "Corporate Gift Product"

            # Determine category
            tl = title_clean.lower()
            matched_cat = None

            # 1. Check prefixes
            for pfx, cat in PREFIX_MAP.items():
                if re.search(r'\b' + pfx + r'[-:\s\d]', title_clean, re.IGNORECASE):
                    matched_cat = cat
                    break

            # 2. Check keywords
            if not matched_cat:
                for cat, kws in KEYWORDS_MAP.items():
                    if any(kw in tl for kw in kws):
                        matched_cat = cat
                        break

            # 3. Default fallback
            if not matched_cat:
                matched_cat = 'gift-boxes'

            # Generate unique SKU
            raw_sku = extract_sku(title_clean, url, matched_cat, len(products) + 101)
            if raw_sku in sku_counter:
                sku_counter[raw_sku] += 1
                final_sku = f"{raw_sku}-{sku_counter[raw_sku]}"
            else:
                sku_counter[raw_sku] = 1
                final_sku = raw_sku

            # If price is 0, assign realistic wholesale benchmark
            if price <= 0:
                p_min, p_max = DEFAULT_PRICES.get(matched_cat, (500, 2500))
                price = random.randint(p_min // 50, p_max // 50) * 50

            # Calculate realistic discount
            discount_pct = random.choice([15, 20, 25, 30])
            original_price = int(round(price * (1 + discount_pct / 100.0) / 50.0) * 50)
            if original_price <= price:
                original_price = price + 200

            # Generate names
            name_en = title_clean
            if not any(final_sku.lower() in name_en.lower().split() for _ in [0]):
                name_en = f"{final_sku} {name_en}"
            name_en = clean_brand(name_en)

            name_bn = clean_brand(generate_bangla_name(final_sku, title_clean, matched_cat))

            # Reviews and Ratings
            rating = round(random.uniform(4.7, 5.0), 1)
            reviews = random.randint(18, 92)
            badge = random.choice(BADGES_POOL)
            min_order = random.choice([10, 20, 25, 50])

            # Description
            description = generate_description(name_en, matched_cat)

            products.append({
                "id": len(products) + 101,
                "section": matched_cat,
                "code": final_sku,
                "nameBn": name_bn,
                "nameEn": name_en,
                "price": price,
                "originalPrice": original_price,
                "rating": rating,
                "reviews": reviews,
                "badge": badge,
                "customizable": True,
                "minOrder": min_order,
                "image": img_url,
                "description": description
            })

    print(f"✓ Total unique products processed: {len(products)}")

    # Save to data/sections.json
    with open(SECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(ALL_SECTIONS, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved {len(ALL_SECTIONS)} sections to {SECTIONS_FILE}")

    # Save to data/products.json
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved {len(products)} products to {PRODUCTS_FILE}")

    # Synchronize assets/js/app.js
    import sys
    sys.path.insert(0, BASE_DIR)
    import server
    server.sync_app_js()

    print("═"*65)
    print("🎉 Full Catalog Import & Synchronization Complete!")
    print("═"*65)

if __name__ == "__main__":
    main()
