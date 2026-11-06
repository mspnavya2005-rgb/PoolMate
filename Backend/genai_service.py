"""Generative-AI module: Smart Ride Recommendation & Trip Insight Generator.

Steps (as required by the brief):
  1. collect ride + passenger preference details
  2. structure the prompt properly
  3. call the LLM API
  4. return meaningful insights/recommendations (shown in the dashboard)
"""
import config

SYSTEM_PROMPT = (
    "You are the smart trip assistant of a car pooling app in Hyderabad, India. "
    "Write short, friendly, practical advice for commuters. Use ONLY the facts given "
    "in the user message; never invent drivers, prices, times or places.")

TASK_FORMAT = """Write the answer under exactly these four headings:
Ride Recommendation: (1-2 sentences, say whether to take this ride and why)
Trip Summary: (1-2 sentences describing who this ride suits, e.g. office commuters, and when)
Route Suitability: (1-2 sentences using the match level, distances and time difference)
Travel Suggestions: (2-3 short practical tips for the passenger)
Keep the whole answer under 140 words."""


def build_ride_prompt(ctx):
    """Structured prompt for a single ride."""
    r, f = ctx["ride"], ctx["ml"]["features"]
    return f"""RIDE DETAILS
- Route: {r['pickup']} -> {r['destination']}
- Departure: {r['depart_time'].replace('T', ' ')}
- Seats available: {r['seats_available']} | Price per seat: Rs {r['price_per_seat']}
- Vehicle: {r['vehicle'] or 'not specified'} | AC: {r['has_ac']} | Smoking: {r['smoking_allowed']} | Music: {r['music']}
- Driver rating: {ctx['driver_rating']}/5

PASSENGER REQUEST
- Wants to travel: {ctx['pickup']} -> {ctx['destination']}
- Preferences: AC={ctx['prefs']['pref_ac']}, no smoking={ctx['prefs']['pref_no_smoking']}, music={ctx['prefs']['pref_music']}

ML RIDE-MATCH RESULT (KNN model)
- Prediction: {ctx['ml']['label']} (confidence {ctx['ml']['confidence']}, score {ctx['ml']['match_score']}/100)
- Pickup distance: {f['pickup_distance_km']} km | Destination distance: {f['destination_distance_km']} km
- Time difference: {int(f['time_diff_min'])} minutes | Preferences satisfied: {f['preference_score']}/3

{TASK_FORMAT}"""


def build_search_prompt(ctx):
    """Structured prompt that compares the top ranked rides for one search."""
    lines = []
    for i, c in enumerate(ctx["top"], 1):
        r = c["ride"]
        lines.append(f"{i}. {r['pickup']} -> {r['destination']} at {r['depart_time'].replace('T', ' ')}, "
                     f"Rs {r['price_per_seat']}/seat, driver rating {c['driver_rating']}, "
                     f"ML: {c['ml']['label']} ({c['ml']['match_score']}/100)")
    return f"""PASSENGER SEARCH
- Wants to travel: {ctx['pickup']} -> {ctx['destination']} around {ctx['when']}
- Preferences: AC={ctx['prefs']['pref_ac']}, no smoking={ctx['prefs']['pref_no_smoking']}, music={ctx['prefs']['pref_music']}

TOP RIDES RANKED BY THE ML MODEL
{chr(10).join(lines)}

Write 3-4 sentences recommending which ride to pick and why (compare match level, price and driver rating),
then one practical travel tip. Keep it under 90 words."""


def _call_llm(prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(model=config.LLM_MODEL, max_tokens=500, system=SYSTEM_PROMPT,
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _offline_note(ctx_kind, ctx):
    """Data-driven plain-text fallback used ONLY when no LLM key/network is available.
    It is built from the live ML result, not a stored answer, and is labelled as such."""
    if ctx_kind == "ride":
        r, m, f = ctx["ride"], ctx["ml"], ctx["ml"]["features"]
        return (f"Ride Recommendation: This ride is a {m['label']} ({m['match_score']}/100) for your request.\n"
                f"Trip Summary: {r['pickup']} to {r['destination']} at {r['depart_time'][11:]}, "
                f"driver rated {ctx['driver_rating']}/5.\n"
                f"Route Suitability: Pickup is {f['pickup_distance_km']} km and drop is "
                f"{f['destination_distance_km']} km from your points; timing differs by {int(f['time_diff_min'])} min.\n"
                "Travel Suggestions: Be at the pickup point 5 minutes early and confirm with the driver.")
    best = ctx["top"][0]
    return (f"Top pick: {best['ride']['pickup']} to {best['ride']['destination']} "
            f"({best['ml']['label']}, {best['ml']['match_score']}/100).")


def generate(kind, ctx):
    prompt = build_ride_prompt(ctx) if kind == "ride" else build_search_prompt(ctx)
    if not config.ANTHROPIC_API_KEY:
        return {"text": _offline_note(kind, ctx), "source": "offline-template",
                "note": "Set ANTHROPIC_API_KEY to enable the LLM-generated insights."}
    try:
        return {"text": _call_llm(prompt), "source": f"llm:{config.LLM_MODEL}"}
    except Exception as e:  # network / quota / bad key
        return {"text": _offline_note(kind, ctx), "source": "offline-template",
                "note": f"LLM call failed ({type(e).__name__}); showing basic summary."}
