"""
Reply keyboard layouts. No inline buttons anywhere — pure ReplyKeyboardMarkup.

Since Telegram Bot API 9.4 (Feb 2026), buttons support a real background
`style`: 'primary' (blue), 'success' (green), 'danger' (red), or None for
the client's neutral default. This requires python-telegram-bot >= 22.7
and a Telegram client updated after Feb 9, 2026 — older clients simply show
the button without special coloring (fully backward compatible).
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def btn(text: str, style: str | None = None) -> KeyboardButton:
    """Shorthand for a single (optionally colored) keyboard button."""
    return KeyboardButton(text=text, style=style)


def _kb(rows, placeholder=None):
    """Shared builder so every keyboard is consistently resized and,
    where useful, shows a placeholder hint in the message input field."""
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def main_menu(is_admin: bool):
    rows = [
        [btn("🏪 Store", "primary"), btn("👤 Profile")],
        [btn("🎫 Redeem Code", "primary"), btn("👥 Referrals")],
        [btn("🎁 Daily Bonus", "success"), btn("🏆 Leaderboard")],
    ]
    if is_admin:
        rows.append([btn("👑 Admin Panel", "primary")])
    return _kb(rows, "Choose an option")


def category_menu(buttons):
    """`buttons` is a list of ready-made labels (e.g. '📖 Ebook') so the
    caller can assign a smart icon per category."""
    rows = []
    for i in range(0, len(buttons), 2):
        chunk = buttons[i:i + 2]
        rows.append([btn(b, "primary") for b in chunk])
    if not rows:
        rows.append([btn("No categories yet")])
    rows.append([btn("🛒 My Purchases")])
    rows.append([btn("🔙 Back")])
    return _kb(rows, "Select a category")


def admin_menu():
    rows = [
        [btn("📊 Stats"), btn("📦 Add Content", "success")],
        [btn("📋 Manage Content"), btn("🎫 Gift Codes", "success")],
        [btn("➕ Add Coins", "success"), btn("➖ Remove Coins", "danger")],
        [btn("👥 Users"), btn("📢 Broadcast", "primary")],
        [btn("🚫 Ban User", "danger"), btn("✅ Unban User", "success")],
        [btn("🔙 Back")],
    ]
    return _kb(rows, "Admin tools")


def cancel_menu(placeholder="Type your response, or tap Cancel"):
    return _kb([[btn("❌ Cancel", "danger")]], placeholder)


def confirm_menu(yes_text="✅ Confirm", no_text="❌ Cancel"):
    """Generic yes/no confirmation keyboard — handy for anything that
    should double-check before acting."""
    return _kb([[btn(yes_text, "success"), btn(no_text, "danger")]], "Please confirm")


def back_to_store():
    return _kb([[btn("🔙 Back")]], "Type the item number to purchase")


def join_gate_menu():
    """Shown when a user hasn't joined the mandatory channel yet."""
    return _kb([[btn("✅ I've Joined", "success")]], "Tap once you've joined the channel")
