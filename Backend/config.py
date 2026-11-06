"""Backend configuration. Everything can be overridden with environment variables."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-in-production")

# Database
#   MySQL  : mysql+pymysql://root:password@localhost:3306/carpool_db   (see schema.sql)
#   Default: SQLite file so the project runs instantly with zero setup.
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "carpool.db"))
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Generative AI (LLM API)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")

TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # login token valid for 7 days
