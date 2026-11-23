"""End-to-end smoke test against a running server (default http://127.0.0.1:8000).

Usage: python scripts/smoke_test.py [base_url]
Creates and then cleans up its own test data.
"""
import sys
from datetime import date, timedelta

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, timeout=15)
ok = 0


def check(name, cond, extra=""):
    global ok
    assert cond, f"FAIL: {name} {extra}"
    ok += 1
    print(f"  ✓ {name}")


# 1. Auth
r = c.post("/api/auth/login", json={"login": "admin", "password": "admin123"})
check("login", r.status_code == 200, r.text)
token = r.json()["token"]
h = {"Authorization": f"Bearer {token}"}
check("bad login rejected", c.post("/api/auth/login", json={"login": "admin", "password": "nope"}).status_code == 401)
check("no token rejected", c.get("/api/clients").status_code == 401)

# 2. Services & settings
services = c.get("/api/services", headers=h).json()
check("services seeded", len(services) >= 5)
svc60 = next(s for s in services if s["duration_min"] == 60)
settings = c.get("/api/settings", headers=h).json()
check("settings", settings["work_start"] == "09:00" and settings["slot_step"] == "30")

# 3. Client CRUD + search
r = c.post("/api/clients", headers=h, json={"name": "Тест Клиент", "phone": "+7 (999) 000-11-22", "notes": "аллергия на ацетон"})
check("client create", r.status_code == 200, r.text)
client = r.json()
check("phone normalized", client["phone"] == "79990001122")
r = c.post("/api/clients", headers=h, json={"name": "Дубль", "phone": "89990001122"})
check("idempotent by phone", r.json()["id"] == client["id"])
check("search by name", any(x["id"] == client["id"] for x in c.get("/api/clients", headers=h, params={"q": "тест кл"}).json()))
check("search by phone", any(x["id"] == client["id"] for x in c.get("/api/clients", headers=h, params={"q": "9990001122"}).json()))

# 4. Slots + appointment lifecycle
day = (date.today() + timedelta(days=2)).isoformat()
slots = c.get("/api/slots", headers=h, params={"date": day, "service_id": svc60["id"]}).json()
free = [s for s in slots if s["available"]]
check("slots generated", len(slots) > 10 and len(free) > 5)
start = free[2]["start"]
r = c.post("/api/appointments", headers=h, json={"client_id": client["id"], "service_id": svc60["id"], "start_at": start})
check("appointment create", r.status_code == 201, r.text)
appt = r.json()
check("end auto-calculated", appt["end_at"] > appt["start_at"])
check("price snapshot", appt["price"] == svc60["price"])
# overlap must be rejected
r = c.post("/api/appointments", headers=h, json={"client_id": client["id"], "service_id": svc60["id"], "start_at": start})
check("overlap rejected 409", r.status_code == 409, r.text)
# cancelled appointment frees the slot
r = c.patch(f"/api/appointments/{appt['id']}", headers=h, json={"status": "cancelled"})
check("status -> cancelled", r.status_code == 200 and r.json()["status"] == "cancelled")
r = c.post("/api/appointments", headers=h, json={"client_id": client["id"], "service_id": svc60["id"], "start_at": start})
check("slot freed after cancel", r.status_code == 201)
appt2 = r.json()
r = c.patch(f"/api/appointments/{appt2['id']}", headers=h, json={"status": "completed", "price": 1800})
check("status -> completed", r.json()["status"] == "completed" and r.json()["price"] == 1800)

# 5. Client history & stats
d = c.get(f"/api/clients/{client['id']}", headers=h).json()
check("client stats", d["stats"]["visits"] == 1 and d["stats"]["total_spent"] == 1800)

# 6. Public booking (no auth!)
pub_services = c.get("/api/public/services").json()
check("public services", len(pub_services) >= 5)
pub_day = (date.today() + timedelta(days=3)).isoformat()
pub_slots = c.get("/api/public/slots", params={"date": pub_day, "service_id": svc60["id"]}).json()
check("public slots only free", all(s["available"] for s in pub_slots) and len(pub_slots) > 5)
r = c.post("/api/public/book", json={"name": "Онлайн Гость", "phone": "89990003344", "service_id": svc60["id"], "start_at": pub_slots[1]["start"], "comment": "френч"})
check("public book", r.status_code == 201, r.text)
# the booking must appear in the owner's calendar immediately
owner_day = c.get("/api/appointments", headers=h, params={"from": pub_day, "to": pub_day}).json()
online = [a for a in owner_day if a["source"] == "online" and a["client"]["phone"] == "79990003344"]
check("online booking in calendar", len(online) == 1)
# same slot must now be rejected
r = c.post("/api/public/book", json={"name": "Ещё Гость", "phone": "89990005566", "service_id": svc60["id"], "start_at": pub_slots[1]["start"]})
check("public double-book rejected", r.status_code == 409)

# 7. Analytics & expenses
r = c.post("/api/expenses", headers=h, json={"date": date.today().isoformat(), "amount": 500, "category": "Материалы"})
check("expense create", r.status_code == 201)
exp_id = r.json()["id"]
today = date.today().isoformat()
summary = c.get("/api/analytics/summary", headers=h, params={"from": today, "to": today}).json()
check("analytics summary", summary["revenue"] >= 0 and "revenue_by_day" in summary and "top_services" in summary)
inactive = c.get("/api/analytics/inactive", headers=h, params={"days": 60}).json()
check("inactive clients", isinstance(inactive, list))

# 8. SPA fallback
check("SPA /", c.get("/").text.find("<div id=\"root\">") >= 0)
check("SPA /book", c.get("/book").text.find("<div id=\"root\">") >= 0)

# 9. Cleanup test data
c.delete(f"/api/appointments/{appt['id']}", headers=h)
c.delete(f"/api/appointments/{appt2['id']}", headers=h)
c.delete(f"/api/appointments/{online[0]['id']}", headers=h)
c.delete(f"/api/clients/{client['id']}", headers=h, params={"force": True})
guest = next(x for x in c.get("/api/clients", headers=h, params={"q": "Онлайн Гость"}).json())
c.delete(f"/api/clients/{guest['id']}", headers=h, params={"force": True})
c.delete(f"/api/expenses/{exp_id}", headers=h)
print(f"\nALL {ok} CHECKS PASSED ✅")
