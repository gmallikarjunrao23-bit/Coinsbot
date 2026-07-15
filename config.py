"""
Configuration for the Premium Content Marketplace Bot.
All sensitive values are loaded from environment variables (.env file).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---- Core Bot Settings ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Comma separated list of admin telegram user IDs, e.g. "6345778491,123456"
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "6345778491").split(",") if x.strip()
]

# PostgreSQL connection string.
# On Railway: add a "Postgres" plugin to your project, then set this variable
# to reference it, e.g. ${{Postgres.DATABASE_URL}} (Railway auto-fills this).
# Locally: point it at any Postgres instance, e.g.
# postgresql://user:password@localhost:5432/premium_bot
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ---- Branding ----
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@DEVILHASHJ")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+cygM0ZXtfDA0Zjk1")

FOOTER = f"\n\n👑 Owner: {OWNER_USERNAME}\n📢 Channel: {CHANNEL_LINK}"

# ---- Economy Settings ----
REFERRAL_BONUS = 5          # coins given to both referrer & new user
DAILY_BONUS_AMOUNT = 10     # coins given for daily bonus
DAILY_BONUS_COOLDOWN_HOURS = 24

# ---- Content Types ----
CONTENT_TYPES = ["course", "file", "method"]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

