"""AI-Enhanced Car Pooling - Flask backend (REST APIs + ML + GenAI integration).

Run:  python app.py        ->  http://127.0.0.1:5000
"""
import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, g, send_from_directory
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import config
from models import db, User, Ride, Booking, driver_avg_rating
import ml_service
import genai_service
from ml_service import LABELS, LOCATIONS_LIST

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config.from_object(config)
CORS(app)
db.init_app(app)
serializer = URLSafeTimedSerializer(config.SECRET_KEY)

with app.app_context():
    db.create_all()


# ----------------------------------------------------------------- helpers
def err(msg, code=400):
    return jsonify({"error": msg}), code


def auth_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return err("Login required", 401)
            try:
                uid = serializer.loads(header[7:], max_age=config.TOKEN_MAX_AGE)["uid"]
            except (BadSignature, SignatureExpired):
                return err("Session expired, please login again", 401)
            user = db.session.get(User, uid)
            if not user:
                return err("User not found", 401)
            if role and user.role != role:
                return err(f"Only {role}s can do this", 403)
            g.user = user
            return fn(*a, **kw)
        return wrapper
    return deco


def parse_dt(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        return None


def desired_datetime(date_s, time_s, ride):
    """Passenger's wanted departure. If no date given, assume the ride's own date."""
    if not time_s:
        return ride.depart_time
    day = date_s or ride.depart_time.strftime("%Y-%m-%d")
    return parse_dt(f"{day}T{time_s}") or ride.depart_time


def match_for(ride, pickup, dest, when, prefs):
    rating = driver_avg_rating(ride.driver_id)
    diff = abs((ride.depart_time - when).total_seconds()) / 60
    ml = ml_service.predict_match(pickup, dest, diff, ride.to_dict(), prefs, rating)
    return ml, rating


def rank_rides(user, data):
    """Search open rides and rank them with the KNN model."""
    pickup, dest = data.get("pickup"), data.get("destination")
    seats = int(data.get("seats") or 1)
    prefs = {k: bool(data.get(k, getattr(user, k))) for k in ("pref_ac", "pref_no_smoking", "pref_music")}
    q = Ride.query.filter(Ride.status == "open", Ride.seats_available >= seats,
                          Ride.depart_time >= datetime.now(), Ride.driver_id != user.id)
    if data.get("date"):
        d = datetime.strptime(data["date"], "%Y-%m-%d")
        q = q.filter(Ride.depart_time >= d, Ride.depart_time < d.replace(hour=23, minute=59))
    out = []
    for ride in q.all():
        when = desired_datetime(data.get("date"), data.get("time"), ride)
        ml, rating = match_for(ride, pickup, dest, when, prefs)
        out.append({"ride": ride.to_dict(rating), "ml": ml, "driver_rating": rating})
    order = {"Best Match": 0, "Suitable Match": 1, "Low Match": 2}
    out.sort(key=lambda c: (order[c["ml"]["label"]], -c["ml"]["match_score"]))
    return out, prefs


# -------------------------------------------------------------------- auth
@app.post("/api/register")
def register():
    d = request.get_json(force=True)
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
    role = d.get("role")
    if not name or "@" not in email or len(pw) < 6:
        return err("Name, valid email and a password of 6+ characters are required")
    if role not in ("driver", "passenger"):
        return err("Role must be driver or passenger")
    if User.query.filter_by(email=email).first():
        return err("Email already registered", 409)
    u = User(name=name, email=email, role=role, phone=(d.get("phone") or "").strip(),
             pref_ac=bool(d.get("pref_ac", False)), pref_no_smoking=bool(d.get("pref_no_smoking", True)),
             pref_music=bool(d.get("pref_music", False)))
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()
    return jsonify({"message": "Registered successfully", "user": u.to_dict()}), 201


@app.post("/api/login")
def login():
    d = request.get_json(force=True)
    u = User.query.filter_by(email=(d.get("email") or "").strip().lower()).first()
    if not u or not u.check_password(d.get("password") or ""):
        return err("Invalid email or password", 401)
    return jsonify({"token": serializer.dumps({"uid": u.id}), "user": u.to_dict()})


@app.get("/api/me")
@auth_required()
def me():
    return jsonify(g.user.to_dict())


@app.put("/api/me/preferences")
@auth_required()
def update_prefs():
    d = request.get_json(force=True)
    for k in ("pref_ac", "pref_no_smoking", "pref_music"):
        if k in d:
            setattr(g.user, k, bool(d[k]))
    db.session.commit()
    return jsonify(g.user.to_dict())


@app.get("/api/locations")
def locations():
    return jsonify(LOCATIONS_LIST)


@app.get("/api/model-info")
def model_info():
    return jsonify(ml_service.model_info())


# --------------------------------------------------------- driver: rides
@app.post("/api/rides")
@auth_required("driver")
def post_ride():
    d = request.get_json(force=True)
    when = parse_dt(d.get("depart_time"))
    if d.get("pickup") not in LOCATIONS_LIST or d.get("destination") not in LOCATIONS_LIST:
        return err("Choose pickup and destination from the list")
    if d["pickup"] == d["destination"]:
        return err("Pickup and destination must be different")
    if not when or when < datetime.now():
        return err("Departure must be a valid future date and time")
    try:
        seats, price = int(d.get("seats")), float(d.get("price_per_seat", 0))
    except (TypeError, ValueError):
        return err("Seats and price must be numbers")
    if not 1 <= seats <= 6 or price < 0:
        return err("Seats must be 1-6 and price cannot be negative")
    r = Ride(driver_id=g.user.id, pickup=d["pickup"], destination=d["destination"], depart_time=when,
             seats_total=seats, seats_available=seats, price_per_seat=price,
             vehicle=(d.get("vehicle") or "").strip(), has_ac=bool(d.get("has_ac", True)),
             smoking_allowed=bool(d.get("smoking_allowed", False)), music=bool(d.get("music", True)))
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@app.get("/api/rides/mine")
@auth_required("driver")
def my_rides():
    rides = Ride.query.filter_by(driver_id=g.user.id).order_by(Ride.depart_time.desc()).all()
    out = []
    for r in rides:
        d = r.to_dict(driver_avg_rating(g.user.id))
        d["bookings"] = [b.to_dict() for b in r.bookings if b.status != "cancelled"]
        out.append(d)
    return jsonify(out)


@app.post("/api/rides/<int:rid>/cancel")
@auth_required("driver")
def cancel_ride(rid):
    r = db.session.get(Ride, rid)
    if not r or r.driver_id != g.user.id:
        return err("Ride not found", 404)
    if r.status != "open":
        return err("Only open rides can be cancelled")
    r.status = "cancelled"
    for b in r.bookings:
        if b.status == "confirmed":
            b.status = "cancelled"
    db.session.commit()
    return jsonify(r.to_dict())


@app.post("/api/rides/<int:rid>/complete")
@auth_required("driver")
def complete_ride(rid):
    r = db.session.get(Ride, rid)
    if not r or r.driver_id != g.user.id:
        return err("Ride not found", 404)
    if r.status != "open":
        return err("Ride is not open")
    r.status = "completed"
    for b in r.bookings:
        if b.status == "confirmed":
            b.status = "completed"
    db.session.commit()
    return jsonify(r.to_dict())


# ------------------------------------------------- passenger: search/book
@app.post("/api/rides/search")
@auth_required("passenger")
def search_rides():
    d = request.get_json(force=True)
    if d.get("pickup") not in LOCATIONS_LIST or d.get("destination") not in LOCATIONS_LIST:
        return err("Choose pickup and destination from the list")
    try:
        ranked, prefs = rank_rides(g.user, d)
    except ValueError:
        return err("Invalid date/seats")
    return jsonify({"results": ranked, "count": len(ranked), "preferences": prefs})


@app.post("/api/bookings")
@auth_required("passenger")
def book_ride():
    d = request.get_json(force=True)
    ride = db.session.get(Ride, d.get("ride_id"))
    seats = int(d.get("seats") or 1)
    pickup = d.get("pickup_point") or (ride.pickup if ride else None)
    drop = d.get("drop_point") or (ride.destination if ride else None)
    if not ride or ride.status != "open":
        return err("Ride not available", 404)
    if ride.depart_time < datetime.now():
        return err("This ride has already departed")
    if ride.driver_id == g.user.id:
        return err("You cannot book your own ride")
    if seats < 1 or seats > ride.seats_available:
        return err(f"Only {ride.seats_available} seat(s) left")
    if pickup not in LOCATIONS_LIST or drop not in LOCATIONS_LIST:
        return err("Invalid pickup/drop point")
    if Booking.query.filter_by(ride_id=ride.id, passenger_id=g.user.id, status="confirmed").first():
        return err("You already booked this ride", 409)
    ml, _ = match_for(ride, pickup, drop, ride.depart_time, g.user.prefs())
    b = Booking(ride_id=ride.id, passenger_id=g.user.id, seats=seats, pickup_point=pickup,
                drop_point=drop, match_label=ml["label"], match_score=ml["match_score"])
    ride.seats_available -= seats
    db.session.add(b)
    db.session.commit()
    return jsonify(b.to_dict()), 201


@app.get("/api/bookings/mine")
@auth_required("passenger")
def my_bookings():
    bs = Booking.query.filter_by(passenger_id=g.user.id).all()
    bs.sort(key=lambda b: b.ride.depart_time)
    return jsonify([b.to_dict() for b in bs])


@app.post("/api/bookings/<int:bid>/cancel")
@auth_required("passenger")
def cancel_booking(bid):
    b = db.session.get(Booking, bid)
    if not b or b.passenger_id != g.user.id:
        return err("Booking not found", 404)
    if b.status != "confirmed":
        return err("Only confirmed bookings can be cancelled")
    b.status = "cancelled"
    b.ride.seats_available = min(b.ride.seats_total, b.ride.seats_available + b.seats)
    db.session.commit()
    return jsonify(b.to_dict())


@app.post("/api/bookings/<int:bid>/rate")
@auth_required("passenger")
def rate_booking(bid):
    d = request.get_json(force=True)
    b = db.session.get(Booking, bid)
    if not b or b.passenger_id != g.user.id:
        return err("Booking not found", 404)
    if b.status != "completed":
        return err("You can rate only completed rides")
    try:
        rating = int(d.get("rating"))
    except (TypeError, ValueError):
        return err("Rating must be 1-5")
    if not 1 <= rating <= 5:
        return err("Rating must be 1-5")
    b.rating, b.review = rating, (d.get("review") or "")[:255]
    db.session.commit()
    return jsonify(b.to_dict())


# ----------------------------------------------------------- ride history
@app.get("/api/history")
@auth_required()
def history():
    """Completed / cancelled rides for the logged-in user (driver or passenger)."""
    if g.user.role == "passenger":
        items = [b.to_dict() for b in Booking.query.filter(
            Booking.passenger_id == g.user.id, Booking.status.in_(["completed", "cancelled"])).all()]
        items.sort(key=lambda x: x["ride"]["depart_time"], reverse=True)
        completed = [i for i in items if i["status"] == "completed"]
        spent = sum(i["seats"] * i["ride"]["price_per_seat"] for i in completed)
        stats = {"completed": len(completed), "cancelled": len(items) - len(completed),
                 "total_spent": round(spent, 2)}
    else:
        rides = Ride.query.filter(Ride.driver_id == g.user.id, Ride.status.in_(["completed", "cancelled"])).all()
        items = [r.to_dict() for r in rides]
        items.sort(key=lambda x: x["depart_time"], reverse=True)
        earned = sum(sum(b.seats for b in r.bookings if b.status == "completed") * r.price_per_seat
                     for r in rides if r.status == "completed")
        stats = {"completed": sum(r.status == "completed" for r in rides),
                 "cancelled": sum(r.status == "cancelled" for r in rides),
                 "total_earned": round(earned, 2), "avg_rating": driver_avg_rating(g.user.id, None)}
    return jsonify({"role": g.user.role, "stats": stats, "items": items})


# ------------------------------------------------------- Generative AI
@app.post("/api/ai/insights")
@auth_required("passenger")
def ai_insights():
    """Trip insight for ONE ride: ML result -> structured prompt -> LLM."""
    d = request.get_json(force=True)
    ride = db.session.get(Ride, d.get("ride_id"))
    if not ride:
        return err("Ride not found", 404)
    pickup = d.get("pickup") if d.get("pickup") in LOCATIONS_LIST else ride.pickup
    dest = d.get("destination") if d.get("destination") in LOCATIONS_LIST else ride.destination
    when = desired_datetime(d.get("date"), d.get("time"), ride)
    prefs = g.user.prefs()
    ml, rating = match_for(ride, pickup, dest, when, prefs)
    ctx = {"ride": ride.to_dict(), "ml": ml, "driver_rating": rating,
           "pickup": pickup, "destination": dest, "prefs": prefs}
    return jsonify({"ml": ml, **genai_service.generate("ride", ctx)})


@app.post("/api/ai/recommendations")
@auth_required("passenger")
def ai_recommendations():
    """Smart recommendation across the top 3 ML-ranked rides of a search."""
    d = request.get_json(force=True)
    if d.get("pickup") not in LOCATIONS_LIST or d.get("destination") not in LOCATIONS_LIST:
        return err("Choose pickup and destination from the list")
    ranked, prefs = rank_rides(g.user, d)
    if not ranked:
        return jsonify({"text": "No rides available for this search yet. Try another time or date.",
                        "source": "none"})
    ctx = {"pickup": d["pickup"], "destination": d["destination"], "prefs": prefs, "top": ranked[:3],
           "when": f"{d.get('date') or 'any date'} {d.get('time') or ''}".strip()}
    return jsonify(genai_service.generate("search", ctx))


# ---------------------------------------------------------------- frontend
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
