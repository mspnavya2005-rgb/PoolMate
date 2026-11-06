"""Loads the trained KNN model and predicts ride compatibility."""
import os, sys, json
import joblib, pandas as pd

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ML"))
sys.path.insert(0, ML_DIR)
from features import FEATURE_COLUMNS, LABELS, build_feature_row  # noqa: E402

MODEL_PATH = os.path.join(ML_DIR, "knn_ride_model.joblib")
_model = None


def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError("Model not found. Run: cd ML && python train_model.py")
        _model = joblib.load(MODEL_PATH)
    return _model


def model_info():
    p = os.path.join(ML_DIR, "model_metrics.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def predict_match(pass_pickup, pass_dest, time_diff_min, ride, pass_prefs, driver_rating):
    """Return dict(label, confidence, match_score, features) for ONE passenger<->ride pair."""
    row = build_feature_row(pass_pickup, pass_dest, time_diff_min, ride, pass_prefs, driver_rating)
    X = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    model = get_model()
    proba = dict(zip(model.classes_, model.predict_proba(X)[0]))
    cls = max(proba, key=proba.get)
    # rank score: P(best)*1 + P(suitable)*0.5  -> 0..100
    score = int(round((proba.get(2, 0) + 0.5 * proba.get(1, 0)) * 100))
    return {"label": LABELS[cls], "confidence": round(float(proba[cls]), 2), "match_score": score,
            "features": dict(zip(FEATURE_COLUMNS, row))}

from features import LOCATIONS  # noqa: E402
LOCATIONS_LIST = sorted(LOCATIONS.keys())
