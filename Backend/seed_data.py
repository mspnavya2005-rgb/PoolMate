"""Optional demo data:  python seed_data.py
Creates demo accounts (password: demo123) and a few upcoming rides."""
from datetime import datetime, timedelta
from app import app
from models import db, User, Ride

def mk_user(name, email, role, **kw):
    u = User.query.filter_by(email=email).first()
    if not u:
        u = User(name=name, email=email, role=role, phone="9999900000", **kw)
        u.set_password("demo123")
        db.session.add(u)
        db.session.flush()
    return u

with app.app_context():
    d1 = mk_user("Ravi Kumar", "driver1@demo.com", "driver")
    d2 = mk_user("Anita Rao", "driver2@demo.com", "driver")
    d3 = mk_user("Suresh Reddy", "driver3@demo.com", "driver")
    mk_user("Priya Sharma", "passenger1@demo.com", "passenger", pref_ac=True, pref_no_smoking=True, pref_music=False)
    mk_user("Arjun Mehta", "passenger2@demo.com", "passenger")
    if Ride.query.count() == 0:
        tomorrow = (datetime.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        at = lambda h, m=0: tomorrow.replace(hour=h, minute=m)
        rides = [
            (d1, "Gachibowli", "Hitech City", at(9, 0), 3, 60, "Honda City", True, False, False),
            (d1, "Gachibowli", "Madhapur", at(9, 30), 2, 70, "Honda City", True, False, True),
            (d2, "Kondapur", "Hitech City", at(8, 45), 3, 50, "Swift Dzire", True, False, False),
            (d2, "Financial District", "Hitech City", at(9, 15), 4, 80, "Innova", True, False, True),
            (d3, "Kukatpally", "Secunderabad", at(18, 0), 3, 90, "Maruti Ertiga", False, True, True),
            (d3, "Ameerpet", "Gachibowli", at(9, 0), 2, 65, "Hyundai i20", True, False, False),
            (d1, "Uppal", "Hitech City", at(8, 30), 3, 120, "Honda City", True, False, False),
        ]
        for dr, p, de, t, s, price, veh, ac, sm, mu in rides:
            db.session.add(Ride(driver_id=dr.id, pickup=p, destination=de, depart_time=t, seats_total=s,
                                seats_available=s, price_per_seat=price, vehicle=veh, has_ac=ac,
                                smoking_allowed=sm, music=mu))
    db.session.commit()
    print("Demo data ready.\n  Driver   : driver1@demo.com / demo123\n  Passenger: passenger1@demo.com / demo123")
