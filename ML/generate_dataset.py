"""Generate a synthetic ride-sharing dataset (ride_dataset.csv).

Each row = one (passenger request, offered ride) pair. The label comes from a
weighted compatibility score + random noise, simulating how real passengers
accept/reject rides. The KNN model LEARNS this pattern from the data - the
backend never hard-codes match results.
"""
import numpy as np, pandas as pd
from features import FEATURE_COLUMNS

rng = np.random.default_rng(42)
N = 3000

pickup_d = np.where(rng.random(N) < 0.45, rng.uniform(0, 2.5, N), rng.uniform(0, 18, N))
dest_d = np.where(rng.random(N) < 0.45, rng.uniform(0, 2.5, N), rng.uniform(0, 18, N))
time_d = np.where(rng.random(N) < 0.5, rng.uniform(0, 30, N), rng.uniform(0, 360, N))
seats = rng.integers(1, 7, N)
pref = rng.integers(0, 4, N)
rating = np.clip(np.round(rng.normal(4.0, 0.7, N), 1), 1, 5)

score = (0.30 * (1 - np.minimum(pickup_d, 12) / 12)
         + 0.30 * (1 - np.minimum(dest_d, 12) / 12)
         + 0.15 * (1 - np.minimum(time_d, 180) / 180)
         + 0.10 * pref / 3
         + 0.10 * (rating - 1) / 4
         + 0.05 * np.minimum(seats, 4) / 4)
score += rng.normal(0, 0.04, N)   # human randomness / noise

label = np.where(score >= 0.72, 2, np.where(score >= 0.48, 1, 0))  # Best / Suitable / Low

df = pd.DataFrame({"pickup_distance_km": pickup_d.round(2),
                   "destination_distance_km": dest_d.round(2),
                   "time_diff_min": time_d.round(0),
                   "seats_available": seats,
                   "preference_score": pref,
                   "driver_rating": rating,
                   "match_label": label})
assert list(df.columns[:-1]) == FEATURE_COLUMNS
df.to_csv("ride_dataset.csv", index=False)
print(df.match_label.value_counts().sort_index().to_string())
print("saved ride_dataset.csv", df.shape)
