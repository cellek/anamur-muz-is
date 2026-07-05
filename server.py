#!/usr/bin/env python3
"""AnamurMuzİş — Anamur muz sektörü iş ilanları sunucusu.

Bağımlılık gerektirmez; Python standart kütüphanesiyle çalışır.
Veriler data.json dosyasında saklanır.

Çalıştırma:  python3 server.py  ->  http://localhost:8756
"""
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "docs")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
PORT = int(os.environ.get("PORT", "8756"))

_lock = threading.Lock()

SEED = {
    "jobs": [
        {
            "id": "seed-job-1",
            "title": "Muz hasadı için 5 işçi aranıyor",
            "employer": "Yılmaz Tarım",
            "location": "Ören Mahallesi",
            "workType": "Hasat",
            "wage": "Günlük 900 TL + yemek",
            "workersNeeded": 5,
            "startDate": "2026-07-10",
            "duration": "2 hafta",
            "phone": "0532 000 00 01",
            "description": "Sera muz hasadı. Deneyimli işçiler tercih edilir. Servis mevcuttur.",
            "createdAt": "2026-07-03T08:00:00+00:00",
        },
        {
            "id": "seed-job-2",
            "title": "Paketleme tesisine eleman alınacak",
            "employer": "Anamur Muz Paketleme",
            "location": "Bahçelievler",
            "workType": "Paketleme",
            "wage": "Aylık 26.000 TL, sigortalı",
            "workersNeeded": 3,
            "startDate": "2026-07-15",
            "duration": "Sürekli",
            "phone": "0532 000 00 02",
            "description": "Muz paketleme ve etiketleme. Kadın-erkek eleman alınacaktır.",
            "createdAt": "2026-07-04T10:30:00+00:00",
        },
    ],
    "workers": [
        {
            "id": "seed-worker-1",
            "name": "Mehmet K.",
            "workTypes": ["Hasat", "Bakım / İlaçlama"],
            "experience": "8 yıl sera muz deneyimi",
            "availableFrom": "2026-07-07",
            "expectedWage": "Günlük 850 TL",
            "location": "Anamur Merkez",
            "phone": "0532 000 00 03",
            "note": "Kendi ulaşımım var, Ören ve Kaledran tarafına gidebilirim.",
            "createdAt": "2026-07-02T09:00:00+00:00",
        }
    ],
}

JOB_FIELDS = {
    "title": (True, 120),
    "employer": (True, 80),
    "location": (True, 80),
    "workType": (True, 40),
    "wage": (True, 80),
    "workersNeeded": (False, 6),
    "startDate": (False, 20),
    "duration": (False, 60),
    "phone": (True, 30),
    "description": (False, 600),
}

WORKER_FIELDS = {
    "name": (True, 80),
    "experience": (False, 200),
    "availableFrom": (False, 20),
    "expectedWage": (False, 80),
    "location": (True, 80),
    "phone": (True, 30),
    "note": (False, 600),
}


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(SEED)
        return json.loads(json.dumps(SEED))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def clean_str(value, max_len):
    if not isinstance(value, str):
        value = str(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:max_len]


def validate(payload, fields):
    item, errors = {}, []
    for name, (required, max_len) in fields.items():
        value = clean_str(payload.get(name, ""), max_len)
        if required and not value:
            errors.append(name)
        item[name] = value
    return item, errors


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > 100_000:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/jobs":
            with _lock:
                data = load_data()
            return self.send_json(sorted(data["jobs"], key=lambda j: j["createdAt"], reverse=True))
        if path == "/api/workers":
            with _lock:
                data = load_data()
            return self.send_json(sorted(data["workers"], key=lambda w: w["createdAt"], reverse=True))
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/jobs":
            return self.create_item("jobs", JOB_FIELDS)
        if path == "/api/workers":
            return self.create_item("workers", WORKER_FIELDS)
        return self.send_json({"error": "Bulunamadı"}, 404)

    def create_item(self, collection, fields):
        payload = self.read_json()
        if payload is None:
            return self.send_json({"error": "Geçersiz istek"}, 400)
        item, errors = validate(payload, fields)
        if errors:
            return self.send_json({"error": "Zorunlu alanlar eksik", "fields": errors}, 400)

        if collection == "jobs":
            try:
                item["workersNeeded"] = max(1, min(999, int(payload.get("workersNeeded", 1))))
            except (TypeError, ValueError):
                item["workersNeeded"] = 1
        else:
            raw_types = payload.get("workTypes", [])
            if not isinstance(raw_types, list):
                raw_types = [raw_types]
            item["workTypes"] = [clean_str(t, 40) for t in raw_types if clean_str(t, 40)][:6]
            if not item["workTypes"]:
                return self.send_json({"error": "Zorunlu alanlar eksik", "fields": ["workTypes"]}, 400)

        item["id"] = uuid.uuid4().hex
        item["createdAt"] = datetime.now(timezone.utc).isoformat()

        with _lock:
            data = load_data()
            data[collection].append(item)
            save_data(data)
        return self.send_json(item, 201)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"AnamurMuzİş çalışıyor: http://localhost:{PORT}")
    server.serve_forever()
