"""Database models (SQLAlchemy - works with MySQL and SQLite)."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'driver' | 'passenger'
    # passenger preferences (used as ML feature "passenger preferences")
    pref_ac = db.Column(db.Boolean, default=False)
    pref_no_smoking = db.Column(db.Boolean, default=True)
    pref_music = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def prefs(self):
        return {"pref_ac": bool(self.pref_ac), "pref_no_smoking": bool(self.pref_no_smoking),
                "pref_music": bool(self.pref_music)}

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "phone": self.phone,
                "role": self.role, **self.prefs()}


class Ride(db.Model):
    __tablename__ = "rides"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    pickup = db.Column(db.String(80), nullable=False)
    destination = db.Column(db.String(80), nullable=False)
    depart_time = db.Column(db.DateTime, nullable=False, index=True)
    seats_total = db.Column(db.Integer, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)
    price_per_seat = db.Column(db.Float, default=0)
    vehicle = db.Column(db.String(80), default="")
    has_ac = db.Column(db.Boolean, default=True)
    smoking_allowed = db.Column(db.Boolean, default=False)
    music = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(12), default="open")  # open | completed | cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    driver = db.relationship("User", backref="rides")

    def to_dict(self, rating=None):
        d = {"id": self.id, "driver_id": self.driver_id, "driver_name": self.driver.name,
             "pickup": self.pickup, "destination": self.destination,
             "depart_time": self.depart_time.strftime("%Y-%m-%dT%H:%M"),
             "seats_total": self.seats_total, "seats_available": self.seats_available,
             "price_per_seat": self.price_per_seat, "vehicle": self.vehicle,
             "has_ac": self.has_ac, "smoking_allowed": self.smoking_allowed,
             "music": self.music, "status": self.status}
        if rating is not None:
            d["driver_rating"] = rating
        return d


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey("rides.id"), nullable=False, index=True)
    passenger_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    seats = db.Column(db.Integer, default=1)
    pickup_point = db.Column(db.String(80), nullable=False)
    drop_point = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(12), default="confirmed")  # confirmed | cancelled | completed
    match_label = db.Column(db.String(20), default="")
    match_score = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer)        # passenger rates the driver (1-5)
    review = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ride = db.relationship("Ride", backref="bookings")
    passenger = db.relationship("User", backref="bookings")

    def to_dict(self):
        return {"id": self.id, "ride": self.ride.to_dict(), "passenger_id": self.passenger_id,
                "passenger_name": self.passenger.name, "seats": self.seats,
                "pickup_point": self.pickup_point, "drop_point": self.drop_point,
                "status": self.status, "match_label": self.match_label,
                "match_score": self.match_score, "rating": self.rating, "review": self.review,
                "booked_on": self.created_at.strftime("%Y-%m-%d %H:%M")}


def driver_avg_rating(driver_id, default=4.0):
    """Average of all passenger ratings this driver has received."""
    avg = (db.session.query(func.avg(Booking.rating)).join(Ride, Booking.ride_id == Ride.id)
           .filter(Ride.driver_id == driver_id, Booking.rating.isnot(None)).scalar())
    return round(float(avg), 1) if avg else default
