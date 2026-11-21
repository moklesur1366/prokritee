#!/usr/bin/env python3
"""
🌿 Prokritee E-commerce Full Backend & Admin Server
Features:
- Session-based Login Authentication for Admin Panel
- User Management (add/edit/delete users, change password)
- REST API for Products (CRUD), Categories, Orders, Stats & Settings
- Direct image file upload (multipart/form-data) stored in assets/images/uploads/
- Live JSON database in data/
- Automatic sync with assets/js/app.js for offline/standalone execution
- Admin Dashboard at http://localhost:5000/admin
"""

import http.server
import socketserver
import webbrowser
import os
import sys
import json
import re
import time
import uuid
import hashlib
import urllib.parse
import urllib.request
import threading
import mimetypes
import email
from email.policy import default

PORT = int(os.environ.get("PORT", 5000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "images", "uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
SECTIONS_FILE = os.path.join(DATA_DIR, "sections.json")
ORDERS_FILE   = os.path.join(DATA_DIR, "orders.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
USERS_FILE    = os.path.join(DATA_DIR, "users.json")
APP_JS_FILE   = os.path.join(BASE_DIR, "assets", "js", "app.js")

# Server tracking & Keep-Alive URL
SERVER_START_TIME = time.time()
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", os.environ.get("PUBLIC_URL", "https://prokritee.onrender.com")).rstrip("/")

# In-memory sessions: {session_token: {username, role, created_at}}
SESSIONS = {}
SESSION_MAX_AGE = 24 * 3600  # 24 hours

# ─── Cloud Storage & Persistence Helpers ─────────────────────────────────────

def save_order_to_cloud(order):
    """Save order to cloud storage (Google Sheet / Supabase) to survive container restarts."""
    # 1. Google Sheets Webhook
    gsheet_url = os.environ.get("GOOGLE_SHEET_WEBHOOK", "").strip()
    if gsheet_url:
        try:
            data = json.dumps(order).encode("utf-8")
            req = urllib.request.Request(
                gsheet_url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"✓ Order {order.get('id')} synced to Google Sheet")
        except Exception as e:
            print(f"Google Sheet sync: {e}")

    # 2. Supabase REST API
    sb_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    sb_key = os.environ.get("SUPABASE_KEY", "").strip()
    if sb_url and sb_key:
        try:
            endpoint = f"{sb_url}/rest/v1/orders"
            payload = json.dumps({
                "id": str(order.get("id")),
                "type": order.get("type", "order"),
                "customer_name": order.get("customerName", ""),
                "company": order.get("company", ""),
                "phone": order.get("phone", ""),
                "address": order.get("address", ""),
                "area": order.get("area", "dhaka"),
                "payment_method": order.get("paymentMethod", "COD"),
                "total": int(order.get("total", 0)),
                "items": order.get("items", []),
                "notes": order.get("notes", ""),
                "status": order.get("status", "Pending"),
                "created_at": order.get("createdAt", time.strftime("%Y-%m-%d %H:%M:%S"))
            }).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "Prefer": "resolution=merge-duplicates"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"✓ Order {order.get('id')} synced to Supabase")
        except Exception as e:
            print(f"Supabase sync: {e}")

def load_orders_from_cloud():
    """Fetch orders from cloud storage if configured."""
    # 1. Supabase
    sb_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    sb_key = os.environ.get("SUPABASE_KEY", "").strip()
    if sb_url and sb_key:
        try:
            endpoint = f"{sb_url}/rest/v1/orders?select=*&order=created_at.desc"
            req = urllib.request.Request(
                endpoint,
                headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                orders = []
                for r in data:
                    orders.append({
                        "id": r.get("id"),
                        "type": r.get("type", "order"),
                        "customerName": r.get("customer_name", ""),
                        "company": r.get("company", ""),
                        "phone": r.get("phone", ""),
                        "address": r.get("address", ""),
                        "area": r.get("area", "dhaka"),
                        "paymentMethod": r.get("payment_method", "COD"),
                        "total": r.get("total", 0),
                        "items": r.get("items", []),
                        "notes": r.get("notes", ""),
                        "status": r.get("status", "Pending"),
                        "createdAt": r.get("created_at", "")
                    })
                return orders
        except Exception as e:
            print(f"Supabase load: {e}")

    # 2. Google Sheets
    gsheet_url = os.environ.get("GOOGLE_SHEET_WEBHOOK", "").strip()
    if gsheet_url:
        try:
            req = urllib.request.Request(gsheet_url, headers={"User-Agent": "Prokritee-Server/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "orders" in data:
                    return data["orders"]
        except Exception as e:
            print(f"Google Sheet load: {e}")

    return None

def get_persisted_orders():
    """Load orders, merging local JSON and cloud orders if available."""
    local_orders = load_json(ORDERS_FILE, [])
    cloud_orders = load_orders_from_cloud()
    if cloud_orders:
        merged = {str(o.get("id")): o for o in local_orders}
        for o in cloud_orders:
            merged[str(o.get("id"))] = o
        orders_list = list(merged.values())
        orders_list.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
        save_json(ORDERS_FILE, orders_list)
        return orders_list
    return local_orders

# ─── Anti-Sleep Keep-Alive Background Thread ──────────────────────────────────

def keep_alive_loop():
    """Background daemon that pings self every 9 minutes to prevent Render Free Tier from idling to sleep."""
    time.sleep(25)  # Wait for server startup
    ping_url = f"{PUBLIC_URL}/api/ping"
    print(f"🔄 Keep-Alive daemon active. Pinging {ping_url} every 9 minutes to stay awake.")
    while True:
        try:
            req = urllib.request.Request(
                ping_url,
                headers={"User-Agent": "Prokritee-KeepAlive-Daemon/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[{time.strftime('%H:%M:%S')}] ✓ Keep-Alive ping OK ({resp.status})")
        except Exception as e:
            # Don't crash if network is temporarily unavailable
            pass
        time.sleep(540)  # 9 minutes (Render sleeps at 15 minutes)

def start_keepalive():
    t = threading.Thread(target=keep_alive_loop, daemon=True)
    t.start()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_json(filepath, default_val=None):
    if default_val is None:
        default_val = []
    if not os.path.exists(filepath):
        save_json(filepath, default_val)
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

def hash_password(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def get_session(handler):
    """Extract session token from Cookie header and validate."""
    cookie_header = handler.headers.get("Cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("pk_session="):
            token = part[len("pk_session="):]
            session = SESSIONS.get(token)
            if session:
                age = time.time() - session.get("created_at", 0)
                if age < SESSION_MAX_AGE:
                    return token, session
                else:
                    SESSIONS.pop(token, None)
    return None, None

def is_authenticated(handler):
    _, session = get_session(handler)
    return session is not None

def ensure_default_admin():
    """Create or enforce admin user. Prioritizes ADMIN_USERNAME & ADMIN_PASSWORD env vars."""
    env_un = os.environ.get("ADMIN_USERNAME", "admin").strip()
    env_pw = os.environ.get("ADMIN_PASSWORD", "").strip()
    users = load_json(USERS_FILE, [])

    if not users:
        pw_to_use = env_pw if env_pw else "admin123"
        users = [{
            "username": env_un,
            "password": hash_password(pw_to_use),
            "role": "admin",
            "fullName": "Administrator"
        }]
        save_json(USERS_FILE, users)
        print(f"ℹ  Created admin user. Username: {env_un}")
    else:
        # If ADMIN_PASSWORD is set in Render environment, ensure it is locked into users.json
        if env_pw:
            target = next((u for u in users if u["username"].lower() == env_un.lower()), None)
            if target:
                target["password"] = hash_password(env_pw)
            else:
                users.append({
                    "username": env_un,
                    "password": hash_password(env_pw),
                    "role": "admin",
                    "fullName": "Administrator"
                })
            save_json(USERS_FILE, users)
            print(f"ℹ  Enforced admin password from environment variable for '{env_un}'.")
    return users

# ─── App.js sync ──────────────────────────────────────────────────────────────

def sync_app_js():
    """Sync data/products.json into assets/js/app.js PRODUCTS array."""
    if not os.path.exists(APP_JS_FILE):
        return
    try:
        products = load_json(PRODUCTS_FILE, [])
        sections = load_json(SECTIONS_FILE, [])
        with open(APP_JS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        prod_json = json.dumps(products, ensure_ascii=False, indent=2)
        new_content = re.sub(
            r"let PRODUCTS = \[.*?\];",
            lambda m: f"let PRODUCTS = {prod_json};",
            content,
            flags=re.DOTALL
        )
        if sections:
            sec_json = json.dumps(sections, ensure_ascii=False, indent=2)
            new_content = re.sub(
                r"let SECTIONS = \[.*?\];",
                lambda m: f"let SECTIONS = {sec_json};",
                new_content,
                flags=re.DOTALL
            )
        with open(APP_JS_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✓ assets/js/app.js synchronized successfully")
    except Exception as e:
        print(f"Sync error: {e}")

# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class ProkriteeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt, *args):
        # Only log API and important requests
        if "/api/" in args[0] or "admin" in args[0]:
            super().log_message(fmt, *args)

    # ── Response helpers ──────────────────────────────────────────────────────

    def send_json_response(self, data, status_code=200, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    # ── OPTIONS (CORS preflight) ──────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        query  = urllib.parse.parse_qs(parsed.query)

        # ── Category page ──
        if path in ("/category", "/category/"):
            self.path = "/category.html"
            return super().do_GET()

        # ── Login page ──
        if path in ("/login", "/login/"):
            self.path = "/login.html"
            return super().do_GET()

        # ── Admin redirect: require login ──
        if path in ("/admin", "/admin/"):
            if not is_authenticated(self):
                return self.redirect("/login")
            self.path = "/admin.html"
            return super().do_GET()

        # ── Public API endpoints (no auth required) ──
        if path == "/api/ping":
            uptime = int(time.time() - SERVER_START_TIME)
            return self.send_json_response({
                "status": "online",
                "service": "Prokritee Store Backend",
                "uptimeSeconds": uptime,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        if path == "/api/products":
            products = load_json(PRODUCTS_FILE, [])
            category = query.get("category", [None])[0]
            search   = query.get("search",   [None])[0]
            filtered = products
            if category and category != "all":
                filtered = [p for p in filtered if p.get("section") == category]
            if search:
                s_lower = search.lower()
                filtered = [p for p in filtered
                    if s_lower in p.get("nameBn","").lower()
                    or s_lower in p.get("nameEn","").lower()
                    or s_lower in p.get("code","").lower()]
            return self.send_json_response(filtered)

        if re.match(r"^/api/products/\d+$", path):
            pid = int(path.split("/")[-1])
            products = load_json(PRODUCTS_FILE, [])
            prod = next((p for p in products if p.get("id") == pid), None)
            if prod:
                return self.send_json_response(prod)
            return self.send_json_response({"error": "Product not found"}, 404)

        if path == "/api/sections":
            return self.send_json_response(load_json(SECTIONS_FILE, []))

        if path == "/api/settings":
            settings = load_json(SETTINGS_FILE, {})
            # Never expose password fields to frontend
            safe = {k: v for k, v in settings.items() if k != "adminPassword"}
            return self.send_json_response(safe)

        if path == "/api/stats":
            products = load_json(PRODUCTS_FILE, [])
            sections = load_json(SECTIONS_FILE, [])
            orders   = get_persisted_orders()
            return self.send_json_response({
                "totalProducts":      len(products),
                "totalSections":      len(sections),
                "totalOrders":        len(orders),
                "totalInventoryValue": sum(p.get("price",0) for p in products),
                "recentProducts":     products[-5:] if products else []
            })

        if path == "/api/orders":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized"}, 401)
            return self.send_json_response(get_persisted_orders())

        # ── Auth check endpoint ──
        if path == "/api/auth-check":
            _, session = get_session(self)
            if session:
                return self.send_json_response({"authenticated": True, "user": session})
            return self.send_json_response({"authenticated": False}, 401)

        # ── User management (admin only) ──
        if path == "/api/users":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized"}, 401)
            users = load_json(USERS_FILE, [])
            safe_users = [{"username": u["username"], "role": u.get("role","admin"), "fullName": u.get("fullName","")} for u in users]
            return self.send_json_response(safe_users)

        # Default static file serving
        return super().do_GET()

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        content_type   = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        # ── LOGIN ──
        if path == "/api/login":
            raw = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw)
            except Exception:
                return self.send_json_response({"error": "Invalid JSON"}, 400)

            username = body.get("username", "").strip()
            password = body.get("password", "")
            users    = load_json(USERS_FILE, [])
            user = next((u for u in users
                         if u["username"].lower() == username.lower()
                         and u["password"] == hash_password(password)), None)
            if user:
                token = str(uuid.uuid4()).replace("-", "")
                SESSIONS[token] = {
                    "username":   user["username"],
                    "role":       user.get("role", "admin"),
                    "fullName":   user.get("fullName", ""),
                    "created_at": time.time()
                }
                cookie = f"pk_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_MAX_AGE}"
                return self.send_json_response(
                    {"success": True, "user": {"username": user["username"], "fullName": user.get("fullName","")}},
                    extra_headers={"Set-Cookie": cookie}
                )
            return self.send_json_response({"error": "Invalid username or password"}, 401)

        # ── LOGOUT ──
        if path == "/api/logout":
            token, _ = get_session(self)
            if token:
                SESSIONS.pop(token, None)
            cookie = "pk_session=; Path=/; Max-Age=0"
            return self.send_json_response({"success": True}, extra_headers={"Set-Cookie": cookie})

        # ── IMAGE UPLOAD (protected) ──
        if path == "/api/upload":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized. Please log in again."}, 401)
            raw_body = self.rfile.read(content_length)
            saved_url = None

            if "multipart/form-data" in content_type:
                header_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
                msg = email.message_from_bytes(header_bytes + raw_body, policy=default)
                for part in msg.iter_parts():
                    filename = part.get_filename()
                    if filename:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
                            ext = ".jpg"
                        clean = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(filename)[0])[:30].strip("_") or "product"
                        new_filename = f"{int(time.time()*1000)}_{clean}{ext}"
                        target_path  = os.path.join(UPLOAD_DIR, new_filename)
                        file_data    = part.get_payload(decode=True)
                        if file_data:
                            with open(target_path, "wb") as f_out:
                                f_out.write(file_data)
                            saved_url = f"assets/images/uploads/{new_filename}"
                            break

            # Fallback if body was sent as JSON with base64
            if not saved_url:
                try:
                    import base64
                    data = json.loads(raw_body.decode("utf-8", errors="ignore"))
                    if "base64" in data:
                        b64 = data["base64"]
                        if "," in b64:
                            b64 = b64.split(",", 1)[1]
                        file_bytes = base64.b64decode(b64)
                        fname = data.get("filename", "image.jpg")
                        ext = os.path.splitext(fname)[1].lower()
                        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
                            ext = ".jpg"
                        clean = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(fname)[0])[:30].strip("_") or "product"
                        new_filename = f"{int(time.time()*1000)}_{clean}{ext}"
                        target_path = os.path.join(UPLOAD_DIR, new_filename)
                        with open(target_path, "wb") as f_out:
                            f_out.write(file_bytes)
                        saved_url = f"assets/images/uploads/{new_filename}"
                except Exception as e:
                    pass

            if saved_url:
                return self.send_json_response({"success": True, "url": saved_url})
            return self.send_json_response({"error": "No valid image uploaded. Please choose a JPG, PNG, or WEBP file."}, 400)

        # ── Parse JSON body for remaining routes ──
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return self.send_json_response({"error": "Invalid JSON format"}, 400)

        # ── CREATE PRODUCT (protected) ──
        if path == "/api/products":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized. Please log in again."}, 401)
            products = load_json(PRODUCTS_FILE, [])
            new_id   = max([int(p.get("id", 100)) for p in products], default=100) + 1

            name_bn = body.get("nameBn", "").strip()
            name_en = body.get("nameEn", "").strip()
            if not name_bn and name_en:
                name_bn = name_en
            if not name_en and name_bn:
                name_en = name_bn
            if not name_bn:
                return self.send_json_response({"error": "Product name is required."}, 400)

            price = int(body.get("price", 0))
            orig_price = int(body.get("originalPrice", 0))
            if orig_price <= 0:
                orig_price = price

            code = body.get("code", "").strip().upper()
            if not code:
                code = f"PK-{new_id}"

            min_order = int(body.get("minOrder", 50))
            if min_order <= 0:
                min_order = 1

            product = {
                "id":            new_id,
                "section":       body.get("section", "gift-boxes"),
                "code":          code,
                "nameBn":        name_bn,
                "nameEn":        name_en,
                "price":         price,
                "originalPrice": orig_price,
                "rating":        float(body.get("rating", 4.8)),
                "reviews":       int(body.get("reviews", 1)),
                "badge":         body.get("badge", "").strip() or "Corporate Gift",
                "customizable":  bool(body.get("customizable", True)),
                "minOrder":      min_order,
                "image":         body.get("image", "").strip() or "assets/images/logo.jpg",
                "description":   body.get("description", "").strip() or "কর্পোরেট কাস্টম লোগো প্রিন্ট ও প্রিমিয়াম বক্স প্যাকেজিং সুবিধা সহ।"
            }
            # Put new product at top of list
            products.insert(0, product)
            save_json(PRODUCTS_FILE, products)
            sync_app_js()
            return self.send_json_response({"success": True, "product": product}, 201)

        # ── CREATE SECTION (protected) ──
        if path == "/api/sections":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized. Please log in again."}, 401)
            sections = load_json(SECTIONS_FILE, [])

            title_bn = body.get("titleBn", "").strip()
            title_en = body.get("titleEn", "").strip()
            if not title_bn and title_en:
                title_bn = title_en
            if not title_en and title_bn:
                title_en = title_bn
            if not title_bn:
                return self.send_json_response({"error": "Category name is required."}, 400)

            # Auto-generate a clean ID / slug if not provided
            sec_id = body.get("id", "").strip().lower()
            if not sec_id:
                clean_slug = re.sub(r"[^a-z0-9]+", "-", title_en.lower()).strip("-")
                sec_id = clean_slug if clean_slug else f"cat-{int(time.time())}"

            # Ensure ID is unique
            base_id = sec_id
            counter = 1
            while any(s.get("id") == sec_id for s in sections):
                counter += 1
                sec_id = f"{base_id}-{counter}"

            desc_bn = body.get("desc", "").strip() or f"{title_bn} কালেকশন ও কর্পোরেট উপহার।"
            desc_en = body.get("descEn", "").strip() or f"{title_en} collection and corporate gifts."
            icon = body.get("icon", "").strip() or "fa-solid fa-gift"
            badge = body.get("badge", "").strip() or "নতুন বিভাগ"
            badge_en = body.get("badgeEn", "").strip() or "New Category"

            section = {
                "id":      sec_id,
                "titleBn": title_bn,
                "titleEn": title_en,
                "desc":    desc_bn,
                "descEn":  desc_en,
                "icon":    icon,
                "badge":   badge,
                "badgeEn": badge_en
            }
            sections.append(section)
            save_json(SECTIONS_FILE, sections)
            sync_app_js()
            return self.send_json_response({"success": True, "section": section}, 201)

        # ── CREATE ORDER ──
        if path == "/api/orders":
            orders   = load_json(ORDERS_FILE, [])
            order_id = body.get("orderId") or f"PK-{int(time.time()*1000)%900000+100000}"
            order = {
                "id":            order_id,
                "type":          body.get("type", "order"),
                "customerName":  body.get("name", ""),
                "company":       body.get("company", ""),
                "phone":         body.get("phone", ""),
                "address":       body.get("address", ""),
                "area":          body.get("area", "dhaka"),
                "paymentMethod": body.get("paymentMethod", "COD"),
                "total":         body.get("total", 0),
                "items":         body.get("items", []),
                "notes":         body.get("notes", ""),
                "status":        "Pending",
                "createdAt":     time.strftime("%Y-%m-%d %H:%M:%S")
            }
            orders.insert(0, order)
            save_json(ORDERS_FILE, orders)
            # Sync to cloud storage if configured
            save_order_to_cloud(order)
            return self.send_json_response({"success": True, "order": order}, 201)

        # ── BULK SYNC / RESTORE ORDERS ──
        if path == "/api/orders/bulk-sync":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized"}, 401)
            incoming = body.get("orders", [])
            if not isinstance(incoming, list):
                return self.send_json_response({"error": "orders must be a list"}, 400)
            existing = load_json(ORDERS_FILE, [])
            merged = {str(o.get("id")): o for o in existing}
            added = 0
            for o in incoming:
                oid = str(o.get("id"))
                if oid and oid not in merged:
                    merged[oid] = o
                    added += 1
                    save_order_to_cloud(o)
            orders_list = list(merged.values())
            orders_list.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
            save_json(ORDERS_FILE, orders_list)
            return self.send_json_response({"success": True, "restored": added, "total": len(orders_list)})

        # ── SETTINGS ──
        if path == "/api/settings":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized"}, 401)
            settings = load_json(SETTINGS_FILE, {})
            settings.update({k: v for k, v in body.items()})
            save_json(SETTINGS_FILE, settings)
            return self.send_json_response({"success": True})

        # ── USER MANAGEMENT: Add user (admin only) ──
        if path == "/api/users":
            if not is_authenticated(self):
                return self.send_json_response({"error": "Unauthorized"}, 401)
            users    = load_json(USERS_FILE, [])
            new_un   = body.get("username","").strip()
            new_pw   = body.get("password","")
            if not new_un or not new_pw:
                return self.send_json_response({"error": "Username and password required"}, 400)
            if any(u["username"].lower() == new_un.lower() for u in users):
                return self.send_json_response({"error": "Username already exists"}, 409)
            users.append({
                "username": new_un,
                "password": hash_password(new_pw),
                "role":     body.get("role", "admin"),
                "fullName": body.get("fullName", "")
            })
            save_json(USERS_FILE, users)
            return self.send_json_response({"success": True}, 201)

        # ── CHANGE PASSWORD (self) ──
        if path == "/api/change-password":
            token, session = get_session(self)
            if not session:
                return self.send_json_response({"error": "Unauthorized"}, 401)
            current_pw = body.get("currentPassword","")
            new_pw     = body.get("newPassword","")
            if not current_pw or not new_pw or len(new_pw) < 4:
                return self.send_json_response({"error": "Invalid password data"}, 400)
            users = load_json(USERS_FILE, [])
            user  = next((u for u in users if u["username"] == session["username"]), None)
            if not user or user["password"] != hash_password(current_pw):
                return self.send_json_response({"error": "Current password is incorrect"}, 403)
            user["password"] = hash_password(new_pw)
            save_json(USERS_FILE, users)
            return self.send_json_response({"success": True})

        return self.send_json_response({"error": "Not Found"}, 404)

    # ── PUT ───────────────────────────────────────────────────────────────────

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        if not is_authenticated(self) and path.startswith("/api/"):
            return self.send_json_response({"error": "Unauthorized"}, 401)

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return self.send_json_response({"error": "Invalid JSON"}, 400)

        # Update product
        if re.match(r"^/api/products/\d+$", path):
            pid      = int(path.split("/")[-1])
            products = load_json(PRODUCTS_FILE, [])
            target   = next((p for p in products if p.get("id") == pid), None)
            if not target:
                return self.send_json_response({"error": "Product not found"}, 404)
            for k in ["section","code","nameBn","nameEn","price","originalPrice",
                      "rating","reviews","badge","customizable","minOrder","image","description"]:
                if k in body:
                    target[k] = body[k]
            if not target.get("nameBn") and target.get("nameEn"):
                target["nameBn"] = target["nameEn"]
            if not target.get("nameEn") and target.get("nameBn"):
                target["nameEn"] = target["nameBn"]
            if target.get("code"):
                target["code"] = str(target["code"]).strip().upper()
            if int(target.get("originalPrice", 0)) <= 0:
                target["originalPrice"] = int(target.get("price", 0))
            save_json(PRODUCTS_FILE, products)
            sync_app_js()
            return self.send_json_response({"success": True, "product": target})

        # Update order status
        if re.match(r"^/api/orders/[^/]+$", path):
            oid    = path.split("/")[-1]
            orders = load_json(ORDERS_FILE, [])
            target = next((o for o in orders if str(o.get("id")) == oid), None)
            if not target:
                return self.send_json_response({"error": "Order not found"}, 404)
            if "status" in body:
                target["status"] = body["status"]
            save_json(ORDERS_FILE, orders)
            return self.send_json_response({"success": True, "order": target})

        # Update section
        if re.match(r"^/api/sections/[^/]+$", path):
            sid      = path.split("/")[-1]
            sections = load_json(SECTIONS_FILE, [])
            target   = next((s for s in sections if s.get("id") == sid), None)
            if not target:
                return self.send_json_response({"error": "Section not found"}, 404)
            target.update(body)
            save_json(SECTIONS_FILE, sections)
            sync_app_js()
            return self.send_json_response({"success": True, "section": target})

        # Update user (by username)
        if re.match(r"^/api/users/[^/]+$", path):
            username = urllib.parse.unquote(path.split("/")[-1])
            users    = load_json(USERS_FILE, [])
            target   = next((u for u in users if u["username"] == username), None)
            if not target:
                return self.send_json_response({"error": "User not found"}, 404)
            if "fullName" in body:
                target["fullName"] = body["fullName"]
            if "role" in body:
                target["role"] = body["role"]
            if "newPassword" in body and body["newPassword"]:
                if len(body["newPassword"]) < 4:
                    return self.send_json_response({"error": "Password too short (min 4 chars)"}, 400)
                target["password"] = hash_password(body["newPassword"])
            save_json(USERS_FILE, users)
            return self.send_json_response({"success": True})

        return self.send_json_response({"error": "Not Found"}, 404)

    # ── DELETE ────────────────────────────────────────────────────────────────

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        if not is_authenticated(self):
            return self.send_json_response({"error": "Unauthorized"}, 401)

        if re.match(r"^/api/products/\d+$", path):
            pid      = int(path.split("/")[-1])
            products = load_json(PRODUCTS_FILE, [])
            orig     = len(products)
            products = [p for p in products if p.get("id") != pid]
            if len(products) == orig:
                return self.send_json_response({"error": "Product not found"}, 404)
            save_json(PRODUCTS_FILE, products)
            sync_app_js()
            return self.send_json_response({"success": True, "deletedId": pid})

        if re.match(r"^/api/sections/[^/]+$", path):
            sid      = path.split("/")[-1]
            sections = load_json(SECTIONS_FILE, [])
            sections = [s for s in sections if s.get("id") != sid]
            save_json(SECTIONS_FILE, sections)
            sync_app_js()
            return self.send_json_response({"success": True, "deletedId": sid})

        if re.match(r"^/api/orders/[^/]+$", path):
            oid    = path.split("/")[-1]
            orders = load_json(ORDERS_FILE, [])
            orders = [o for o in orders if str(o.get("id")) != oid]
            save_json(ORDERS_FILE, orders)
            return self.send_json_response({"success": True, "deletedId": oid})

        if re.match(r"^/api/users/[^/]+$", path):
            username = urllib.parse.unquote(path.split("/")[-1])
            _, session = get_session(self)
            if session and session["username"] == username:
                return self.send_json_response({"error": "Cannot delete your own account"}, 400)
            users    = load_json(USERS_FILE, [])
            orig     = len(users)
            users    = [u for u in users if u["username"] != username]
            if len(users) == orig:
                return self.send_json_response({"error": "User not found"}, 404)
            if not users:
                return self.send_json_response({"error": "Cannot delete the last admin user"}, 400)
            save_json(USERS_FILE, users)
            return self.send_json_response({"success": True})

        return self.send_json_response({"error": "Not Found"}, 404)


# ─── Start Server ─────────────────────────────────────────────────────────────

def start_server():
    global PORT
    ensure_default_admin()
    is_cloud = "PORT" in os.environ
    max_attempts = 1 if is_cloud else 10
    for attempt in range(max_attempts):
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", PORT), ProkriteeHandler) as httpd:
                url       = f"http://localhost:{PORT}"
                admin_url = f"http://localhost:{PORT}/admin"
                login_url = f"http://localhost:{PORT}/login"
                print("\n" + "="*65)
                print("🌿 PROKRITEE E-COMMERCE BACKEND & STORE SERVER IS RUNNING")
                print("="*65)
                print(f"👉 Public Website:  {url}")
                print(f"🔐 Admin Login:     {login_url}")
                print(f"⚙️  Admin Dashboard: {admin_url}")
                print(f"📁 Root Directory:  {BASE_DIR}")
                print(f"📦 Uploads Folder:  {UPLOAD_DIR}")
                print("="*65)
                print("Default Admin — Username: admin  |  Password: admin123")
                print("Press Ctrl+C to stop.\n")
                # Start Keep-Alive daemon to prevent cloud sleep
                start_keepalive()
                if not is_cloud:
                    try:
                        webbrowser.open(login_url)
                    except Exception:
                        pass
                httpd.serve_forever()
                break
        except OSError:
            if is_cloud:
                raise
            PORT += 1

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nServer stopped gracefully.")
        sys.exit(0)
