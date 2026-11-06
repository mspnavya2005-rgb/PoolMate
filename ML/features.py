"""Shared feature engineering for the ride-match model.

Used by the training script, the notebook AND the Flask backend so that the
exact same transformation is applied at training time and prediction time.
"""
import math

# Hyderabad localities with (latitude, longitude) - used for distance features.
LOCATIONS = {
    "Gachibowli": (17.4401, 78.3489),
    "Hitech City": (17.4435, 78.3772),
    "Madhapur": (17.4483, 78.3915),
    "Kondapur": (17.4600, 78.3640),
    "Financial District": (17.4172, 78.3430),
    "Jubilee Hills": (17.4326, 78.4071),
    "Banjara Hills": (17.4156, 78.4347),
    "Ameerpet": (17.4375, 78.4482),
    "Kukatpally": (17.4948, 78.3996),
    "Secunderabad": (17.4399, 78.4983),
    "Begumpet": (17.4440, 78.4676),
    "Uppal": (17.4058, 78.5591),
    "LB Nagar": (17.3457, 78.5522),
    "Dilsukhnagar": (17.3688, 78.5247),
    "Mehdipatnam": (17.3950, 78.4399),
    "Miyapur": (17.4968, 78.3614),
    "Charminar": (17.3616, 78.4747),
    "Shamshabad Airport": (17.2403, 78.4294),
}

LABELS = ["Low Match", "Suitable Match", "Best Match"]  # index = class id

FEATURE_COLUMNS = [
    "pickup_distance_km",       # passenger pickup  <-> ride pickup
    "destination_distance_km",  # passenger drop    <-> ride destination
    "time_diff_min",            # |wanted time - departure time|
    "seats_available",
    "preference_score",         # 0-3 matching passenger preferences
    "driver_rating",            # average previous ride rating (1-5)
]


def haversine_km(a, b):
    """Great-circle distance in km between two (lat, lon) tuples."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def location_distance(name_a, name_b):
    if name_a not in LOCATIONS or name_b not in LOCATIONS:
        return 25.0  # unknown place -> treat as far away
    return haversine_km(LOCATIONS[name_a], LOCATIONS[name_b])


def preference_score(pass_prefs, ride):
    """How many of the 3 passenger preferences the ride satisfies (0-3)."""
    s = 0
    s += int((not pass_prefs.get("pref_ac")) or ride.get("has_ac"))
    s += int((not pass_prefs.get("pref_no_smoking")) or (not ride.get("smoking_allowed")))
    s += int(bool(pass_prefs.get("pref_music")) == bool(ride.get("music")))
    return s


def build_feature_row(pass_pickup, pass_dest, time_diff_min, ride, pass_prefs, driver_rating):
    return [
        round(location_distance(pass_pickup, ride["pickup"]), 3),
        round(location_distance(pass_dest, ride["destination"]), 3),
        float(min(abs(time_diff_min), 360)),
        int(ride["seats_available"]),
        preference_score(pass_prefs, ride),
        float(driver_rating),
    ]
