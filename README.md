# 🚗 AI-Enhanced Car Pooling Application

A full-stack car pooling platform where **drivers offer rides**, **passengers search and book them**, and two AI modules make it smarter:

* **Machine Learning (KNN, scikit-learn)** – predicts ride compatibility: *Best Match / Suitable Match / Low Match*.
* **Generative AI (LLM API)** – writes smart ride recommendations, trip summaries, route-suitability insights and travel suggestions, shown in the dashboard.

## Project structure

```
AI_Car_Pooling/
├── Frontend/            HTML, CSS, JS (index.html, style.css, app.js)
├── Backend/             Flask REST APIs + ML + GenAI integration
│   ├── app.py           all API routes (auth, rides, bookings, history, AI)
│   ├── models.py        SQLAlchemy models (users, rides, bookings)
│   ├── ml_service.py    loads the saved KNN model and predicts matches
│   ├── genai_service.py structured prompts + LLM API call
│   ├── config.py        settings (DB url, API key, model name)
│   ├── schema.sql       MySQL schema (optional)
│   ├── seed_data.py     demo accounts + sample rides (optional)
│   ├── test_api.py      end-to-end test of the backend
│   └── requirements.txt
├── ML/                  Model training code, dataset, saved model
│   ├── features.py      feature engineering shared with the backend
│   ├── generate_dataset.py → ride_dataset.csv
│   ├── train_model.py   → knn_ride_model.joblib + model_metrics.json
│   └── ride_match_knn.ipynb   preprocessing, training, evaluation
├── Project_Documentation.docx
├── DEMO_VIDEO_SCRIPT.md
└── README.md
```

## Setup (about 3 minutes)

Requirements: **Python 3.9+** (nothing else is needed).

```bash
# 1. create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. install dependencies
cd Backend
pip install -r requirements.txt
```

The trained model (`ML/knn_ride_model.joblib`) and dataset are already included.
To retrain from scratch: `cd ML && python generate_dataset.py && python train_model.py`

### Generative AI key (LLM API)

The GenAI module calls an LLM API (Anthropic Claude). Set your key before starting the server:

```bash
set ANTHROPIC_API_KEY=your_key_here          # Windows (cmd)
$env:ANTHROPIC_API_KEY="your_key_here"       # Windows (PowerShell)
export ANTHROPIC_API_KEY=your_key_here       # macOS / Linux
```

Optional: `LLM_MODEL` (default `claude-sonnet-5-5`). Without a key the app still runs, and the
insight box shows a basic summary built from the live ML result with a note asking for the key.
**Use your key for the demo video so real LLM text is displayed.**

### Database

* **Default: SQLite** – zero setup, a `carpool.db` file is created automatically.
* **MySQL (as in the brief):** create the empty database and set the URL, e.g.

  ```bash
  mysql -u root -p -e "CREATE DATABASE carpool_db CHARACTER SET utf8mb4;"
  set DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/carpool_db
  ```
  Tables are created automatically on first run (`schema.sql` shows the same structure).

## Steps to run

```bash
cd Backend
python seed_data.py      # optional: demo users + sample rides for tomorrow
python app.py
```

Open **http://127.0.0.1:5000** (Flask serves the frontend too).

Demo logins (password `demo123`): `driver1@demo.com`, `driver2@demo.com`, `passenger1@demo.com`, `passenger2@demo.com`.

Run the automated test: `cd Backend && python test_api.py` → prints `ALL TESTS PASSED`.

## How it works

1. **Driver** registers, posts a ride (route, time, seats, price, AC/smoking/music) and manages it in the dashboard.
2. **Passenger** searches by pickup, destination, date, time, seats and preferences.
3. The backend turns every open ride into **6 features** – pickup distance, destination distance, time difference, available seats, preference score, driver rating – and the **KNN model** predicts *Best / Suitable / Low Match*. Rides are ranked by it.
4. For the top rides, a **structured prompt** (ride details + passenger preferences + ML result) is sent to the **LLM**, which returns a recommendation, trip summary, route suitability and travel tips – displayed in the dashboard.
5. Passenger books (seats are reduced), sees the travel schedule, can cancel, and rates the driver after completion; ratings feed back into the ML feature *driver rating*.
6. **Ride history dashboards** show completed / cancelled rides, spending (passenger) or earnings and rating (driver).

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/register`, `/api/login` | registration & login (token) |
| POST | `/api/rides` | driver posts a ride |
| GET | `/api/rides/mine` | driver dashboard |
| POST | `/api/rides/<id>/complete`, `/cancel` | manage ride |
| POST | `/api/rides/search` | **ML-ranked** ride search |
| POST | `/api/bookings` | book a ride |
| GET | `/api/bookings/mine` | passenger schedule |
| POST | `/api/bookings/<id>/cancel`, `/rate` | cancel / rate |
| GET | `/api/history` | ride history dashboard |
| POST | `/api/ai/insights`, `/api/ai/recommendations` | **GenAI** insights |

## Notes

* The dataset is **synthetic** (generated from a compatibility rule + random noise). The model *learns* from it; match results and AI text are never hard-coded in the app.
* Replace `SECRET_KEY` (environment variable) before any real deployment.
