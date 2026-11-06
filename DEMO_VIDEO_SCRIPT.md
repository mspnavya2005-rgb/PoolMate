# Demo Video Script (record 5–10 minutes)

Record your screen with your voice (Windows: **Win + G** Game Bar, or OBS / Zoom). Set `ANTHROPIC_API_KEY` first so the real GenAI text appears. Run `python seed_data.py` and `python app.py`, then open http://127.0.0.1:5000.

| Time | What to show | What to say |
|---|---|---|
| 0:00 – 0:40 | Introduction, folder structure (Frontend / Backend / ML) | Project name, your name, problem: finding shared rides; solution uses full stack + ML + GenAI |
| 0:40 – 1:30 | Register a new **driver** and a new **passenger** (show passenger preferences) | User registration & login, roles |
| 1:30 – 3:00 | Login as driver → **Post a Ride** (Gachibowli → Hitech City, tomorrow 9:00) → open **My Rides Dashboard** | Driver ride posting, pickup & destination management, seats, price, AC/smoking/music |
| 3:00 – 5:00 | Login as passenger → **Find Rides** → search → show **Best / Suitable / Low Match** badges and the distances, time difference | **ML-based ride matching**: KNN with 6 features, ranking |
| 5:00 – 6:30 | Click **AI insight** on a ride and read the **AI recommendation** box | **GenAI**: prompt = ride details + preferences + ML result → LLM → recommendation, summary, route suitability, travel tips |
| 6:30 – 7:30 | **Book** a ride → **My Bookings & Schedule** → login as driver, show the passenger in the dashboard | Ride booking workflow, seat count updates, travel schedule |
| 7:30 – 8:30 | Driver clicks **Mark completed** → passenger **Rate driver** → **Ride History** (both roles) | Ride history dashboard, rating feeds back into the model feature |
| 8:30 – 10:00 | Open `ML/ride_match_knn.ipynb` (accuracy ≈ 83%, confusion matrix), `Backend/ml_service.py`, `Backend/genai_service.py` (the prompt) | **Basic explanation of your code**: dataset → preprocessing → KNN → joblib → backend; prompt structure → LLM API |

Checklist from the brief: ride posting & booking workflow ✔, passenger and driver dashboards ✔, complete application walkthrough ✔, ML-based ride matching ✔, GenAI trip recommendation ✔, basic code explanation ✔.
