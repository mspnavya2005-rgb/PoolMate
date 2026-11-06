"""End-to-end smoke test of the whole backend (uses a temporary database).
Run:  python test_api.py"""
import os, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
from datetime import datetime, timedelta
from unittest import mock
from app import app
import genai_service

c = app.test_client()
H = lambda t: {"Authorization": f"Bearer {t}"}
def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.get_json())
    return r.get_json()

# register + login
ok(c.post("/api/register", json={"name": "Drv", "email": "d@x.com", "password": "secret1", "role": "driver"}), 201)
ok(c.post("/api/register", json={"name": "Pas", "email": "p@x.com", "password": "secret1", "role": "passenger", "pref_ac": True}), 201)
assert c.post("/api/register", json={"name": "Pas", "email": "p@x.com", "password": "secret1", "role": "passenger"}).status_code == 409
assert c.post("/api/login", json={"email": "d@x.com", "password": "bad"}).status_code == 401
dt = ok(c.post("/api/login", json={"email": "d@x.com", "password": "secret1"}))["token"]
pt = ok(c.post("/api/login", json={"email": "p@x.com", "password": "secret1"}))["token"]

# driver posts rides; role protection
tm = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0)
ride = lambda p, d, t: {"pickup": p, "destination": d, "depart_time": t.strftime("%Y-%m-%dT%H:%M"),
                        "seats": 3, "price_per_seat": 60, "vehicle": "Swift"}
r1 = ok(c.post("/api/rides", json=ride("Gachibowli", "Hitech City", tm), headers=H(dt)), 201)
ok(c.post("/api/rides", json=ride("Uppal", "Shamshabad Airport", tm + timedelta(hours=5)), headers=H(dt)), 201)
assert c.post("/api/rides", json=ride("Uppal", "Uppal", tm), headers=H(dt)).status_code == 400
assert c.post("/api/rides", json=ride("Gachibowli", "Hitech City", tm), headers=H(pt)).status_code == 403

# passenger search -> ML ranking
res = ok(c.post("/api/rides/search", json={"pickup": "Gachibowli", "destination": "Hitech City",
        "date": tm.strftime("%Y-%m-%d"), "time": "09:00", "seats": 1}, headers=H(pt)))
print("Search ->", [(x["ride"]["pickup"], x["ml"]["label"], x["ml"]["match_score"]) for x in res["results"]])
assert res["results"][0]["ml"]["label"] == "Best Match"
assert res["results"][0]["ride"]["id"] == r1["id"]

# GenAI: offline path, then mocked LLM path (prompt must contain ML result)
ins = ok(c.post("/api/ai/insights", json={"ride_id": r1["id"], "pickup": "Gachibowli", "destination": "Hitech City"}, headers=H(pt)))
print("AI (no key) ->", ins["source"])
with mock.patch.object(genai_service.config, "ANTHROPIC_API_KEY", "fake"), \
     mock.patch.object(genai_service, "_call_llm", return_value="LLM TEXT") as m:
    ins = ok(c.post("/api/ai/insights", json={"ride_id": r1["id"]}, headers=H(pt)))
    assert ins["text"] == "LLM TEXT" and ins["source"].startswith("llm")
    assert "Best Match" in m.call_args[0][0] and "RIDE DETAILS" in m.call_args[0][0]
    rec = ok(c.post("/api/ai/recommendations", json={"pickup": "Gachibowli", "destination": "Hitech City"}, headers=H(pt)))
    assert rec["text"] == "LLM TEXT"

# booking flow
b = ok(c.post("/api/bookings", json={"ride_id": r1["id"], "seats": 2}, headers=H(pt)), 201)
assert b["match_label"] == "Best Match"
assert c.post("/api/bookings", json={"ride_id": r1["id"], "seats": 1}, headers=H(pt)).status_code == 409
mine = ok(c.get("/api/rides/mine", headers=H(dt)))
assert mine[-1]["seats_available"] == 1 or any(x["seats_available"] == 1 for x in mine)
ok(c.post(f"/api/bookings/{b['id']}/cancel", headers=H(pt)))
b = ok(c.post("/api/bookings", json={"ride_id": r1["id"], "seats": 1}, headers=H(pt)), 201)

# complete -> rate -> history
assert c.post(f"/api/bookings/{b['id']}/rate", json={"rating": 5}, headers=H(pt)).status_code == 400
ok(c.post(f"/api/rides/{r1['id']}/complete", headers=H(dt)))
ok(c.post(f"/api/bookings/{b['id']}/rate", json={"rating": 5, "review": "great"}, headers=H(pt)))
hp = ok(c.get("/api/history", headers=H(pt)))
hd = ok(c.get("/api/history", headers=H(dt)))
print("Passenger history:", hp["stats"], "| Driver history:", hd["stats"])
assert hd["stats"]["avg_rating"] == 5.0 and hp["stats"]["completed"] == 1
print("ALL TESTS PASSED")
