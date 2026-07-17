"""
Database layer for the Premium Content Marketplace Bot.
Uses PostgreSQL (designed for Railway's built-in Postgres plugin).
"""
import random
import string
from datetime import datetime, timedelta
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import DATABASE_URL, REFERRAL_BONUS


def _normalize_url(url: str) -> str:
    # Some providers (Railway included, historically) hand out "postgres://"
    # while psycopg2 expects "postgresql://" — normalize just in case.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def now():
    return datetime.utcnow()


class Database:
    def __init__(self, url=DATABASE_URL):
        if not url:
            raise SystemExit(
                "DATABASE_URL is not set. Add a Postgres plugin on Railway "
                "(or point this at any Postgres instance) and set DATABASE_URL."
            )
        self.url = _normalize_url(url)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = psycopg2.connect(self.url)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _cursor(self, conn):
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def _init_db(self):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    coins INTEGER DEFAULT 0,
                    referred_by BIGINT DEFAULT 0,
                    referral_count INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    daily_bonus_claimed TIMESTAMP,
                    banned INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    type TEXT,
                    price INTEGER,
                    file_id TEXT,
                    file_name TEXT,
                    text_content TEXT,
                    created_at TIMESTAMP,
                    active INTEGER DEFAULT 1,
                    total_sold INTEGER DEFAULT 0
                )
            """)
            # Migration: older deployments may be missing this column.
            cur.execute("ALTER TABLE content ADD COLUMN IF NOT EXISTS text_content TEXT")
            # Migration: earlier versions restricted "type" to a fixed set
            # (course/file/method) via a CHECK constraint. Drop it so admins
            # can add ANY category of content. Safe/no-op if already absent.
            cur.execute("ALTER TABLE content DROP CONSTRAINT IF EXISTS content_type_check")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    content_id INTEGER,
                    content_type TEXT,
                    price INTEGER,
                    purchased_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gift_codes (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE,
                    coins INTEGER,
                    claimed_by BIGINT DEFAULT 0,
                    created_by BIGINT,
                    created_at TIMESTAMP,
                    used_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    max_uses INTEGER DEFAULT 1,
                    used_count INTEGER DEFAULT 0
                )
            """)
            # Migration: older deployments may be missing these columns.
            cur.execute("ALTER TABLE gift_codes ADD COLUMN IF NOT EXISTS max_uses INTEGER DEFAULT 1")
            cur.execute("ALTER TABLE gift_codes ADD COLUMN IF NOT EXISTS used_count INTEGER DEFAULT 0")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gift_code_redemptions (
                    id SERIAL PRIMARY KEY,
                    code TEXT,
                    user_id BIGINT,
                    redeemed_at TIMESTAMP,
                    UNIQUE(code, user_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS referral_codes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    code TEXT UNIQUE,
                    created_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    type TEXT,
                    amount INTEGER,
                    description TEXT,
                    created_at TIMESTAMP
                )
            """)
            cur.close()

    # ---------------- USER METHODS ----------------
    def get_user(self, user_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None

    def create_user(self, user_id, username, first_name, referred_by=0):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                INSERT INTO users
                (user_id, username, first_name, coins, referred_by, referral_count,
                 total_spent, daily_bonus_claimed, banned, created_at, last_active)
                VALUES (%s, %s, %s, 0, %s, 0, 0, NULL, 0, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, username or "", first_name or "", referred_by, now(), now()))
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            cur.execute("""
                INSERT INTO referral_codes (user_id, code, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, code, now()))
            cur.close()

    def touch_last_active(self, user_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET last_active=%s WHERE user_id=%s", (now(), user_id))
            cur.close()

    def update_coins(self, user_id, delta, tx_type="adjust", description=""):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET coins = coins + %s WHERE user_id=%s", (delta, user_id))
            cur.execute("""
                INSERT INTO transactions (user_id, type, amount, description, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, tx_type, delta, description, now()))
            cur.close()

    def apply_referral(self, new_user_id, referrer_id):
        """Grant bonus coins to both new user and referrer."""
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET referred_by=%s WHERE user_id=%s", (referrer_id, new_user_id))
            cur.close()
        self.update_coins(new_user_id, REFERRAL_BONUS, "referral_join", "Joined via referral")
        self.update_coins(referrer_id, REFERRAL_BONUS, "referral_bonus", f"Referred user {new_user_id}")
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=%s", (referrer_id,))
            cur.close()

    def can_claim_daily(self, user_id):
        user = self.get_user(user_id)
        if not user or not user["daily_bonus_claimed"]:
            return True
        last = user["daily_bonus_claimed"]
        return datetime.utcnow() - last >= timedelta(hours=24)

    def claim_daily(self, user_id, amount):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET daily_bonus_claimed=%s WHERE user_id=%s", (now(), user_id))
            cur.close()
        self.update_coins(user_id, amount, "daily_bonus", "Daily bonus claimed")

    def set_ban(self, user_id, banned: bool):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE users SET banned=%s WHERE user_id=%s", (1 if banned else 0, user_id))
            cur.close()

    def is_banned(self, user_id):
        u = self.get_user(user_id)
        return bool(u and u["banned"])

    def get_all_users(self):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    def get_leaderboard(self, limit=10):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute(
                "SELECT * FROM users WHERE banned=0 ORDER BY coins DESC LIMIT %s", (limit,)
            )
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    # ---------------- CONTENT METHODS ----------------
    def add_content(self, title, description, ctype, price, file_id, file_name, text_content=None):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                INSERT INTO content (title, description, type, price, file_id, file_name, text_content, created_at, active, total_sold)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 0)
                RETURNING id
            """, (title, description, ctype, price, file_id, file_name, text_content, now()))
            new_id = cur.fetchone()["id"]
            cur.close()
            return new_id

    def get_content_by_type(self, ctype):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute(
                "SELECT * FROM content WHERE type=%s AND active=1 ORDER BY id DESC", (ctype,)
            )
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    def get_distinct_types(self):
        """Every distinct category currently in use — powers the dynamic
        store menu so any category an admin adds shows up automatically."""
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute(
                "SELECT DISTINCT type FROM content WHERE active=1 AND type IS NOT NULL ORDER BY type ASC"
            )
            rows = cur.fetchall()
            cur.close()
            return [r["type"] for r in rows]

    def get_content_by_id(self, content_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM content WHERE id=%s", (content_id,))
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None

    def get_all_content(self):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM content ORDER BY id DESC")
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    def increment_sold(self, content_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("UPDATE content SET total_sold = total_sold + 1 WHERE id=%s", (content_id,))
            cur.close()

    def delete_content(self, content_id):
        """Permanently removes a content item (used by the admin 🗑️ remove flow)."""
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("DELETE FROM content WHERE id=%s", (content_id,))
            deleted = cur.rowcount > 0
            cur.close()
            return deleted

    # ---------------- PURCHASE METHODS ----------------
    def record_purchase(self, user_id, content_id, content_type, price):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                INSERT INTO purchases (user_id, content_id, content_type, price, purchased_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, content_id, content_type, price, now()))
            cur.execute("UPDATE users SET total_spent = total_spent + %s WHERE user_id=%s", (price, user_id))
            cur.close()

    def get_purchases(self, user_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                SELECT p.*, ct.title, ct.file_id, ct.file_name
                FROM purchases p LEFT JOIN content ct ON p.content_id = ct.id
                WHERE p.user_id=%s ORDER BY p.purchased_at DESC
            """, (user_id,))
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    def has_purchased(self, user_id, content_id):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute(
                "SELECT 1 FROM purchases WHERE user_id=%s AND content_id=%s", (user_id, content_id)
            )
            row = cur.fetchone()
            cur.close()
            return bool(row)

    # ---------------- GIFT CODE METHODS ----------------
    def generate_gift_code(self, coins, created_by, max_uses=1):
        """Creates ONE code that can be redeemed by up to `max_uses`
        different users, each receiving `coins` coins (once per user)."""
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("""
                INSERT INTO gift_codes (code, coins, claimed_by, created_by, created_at, used_at, is_active, max_uses, used_count)
                VALUES (%s, %s, 0, %s, %s, NULL, 1, %s, 0)
            """, (code, coins, created_by, now(), max_uses))
            cur.close()
        return code

    def redeem_gift_code(self, code, user_id):
        """Returns (coins, status). status is one of:
        'ok', 'not_found', 'already_redeemed', 'exhausted'."""
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM gift_codes WHERE code=%s", (code,))
            row = cur.fetchone()
            if not row:
                cur.close()
                return None, "not_found"

            cur.execute(
                "SELECT 1 FROM gift_code_redemptions WHERE code=%s AND user_id=%s", (code, user_id)
            )
            if cur.fetchone():
                cur.close()
                return None, "already_redeemed"

            if row["used_count"] >= row["max_uses"]:
                cur.close()
                return None, "exhausted"

            cur.execute(
                "INSERT INTO gift_code_redemptions (code, user_id, redeemed_at) VALUES (%s, %s, %s)",
                (code, user_id, now()),
            )
            new_used_count = row["used_count"] + 1
            still_active = 1 if new_used_count < row["max_uses"] else 0
            cur.execute(
                "UPDATE gift_codes SET used_count=%s, is_active=%s, used_at=%s WHERE code=%s",
                (new_used_count, still_active, now(), code),
            )
            coins = row["coins"]
            cur.close()
        self.update_coins(user_id, coins, "gift_code", f"Redeemed code {code}")
        return coins, "ok"

    def get_all_gift_codes(self):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT * FROM gift_codes ORDER BY id DESC")
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

    # ---------------- STATS ----------------
    def get_stats(self):
        with self._conn() as c:
            cur = self._cursor(c)
            cur.execute("SELECT COUNT(*) AS n FROM users")
            total_users = cur.fetchone()["n"]
            cur.execute("SELECT COALESCE(SUM(coins),0) AS n FROM users")
            total_coins = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM content")
            total_content = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM purchases")
            total_sales = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM users WHERE created_at::date = CURRENT_DATE")
            new_today = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM users WHERE last_active::date = CURRENT_DATE")
            active_today = cur.fetchone()["n"]
            cur.close()
            return {
                "total_users": total_users,
                "total_coins": total_coins,
                "total_content": total_content,
                "total_sales": total_sales,
                "new_today": new_today,
                "active_today": active_today,
            }

