"""
Reply keyboard layouts. No inline buttons anywhere — pure ReplyKeyboardMarkup,
but each menu has its own distinct visual "skin" and a helpful input
placeholder, so navigating the bot feels premium, guided, and varied.
"""
from telegram import ReplyKeyboardMarkup


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
        ["🏪 STORE", "👤 PROFILE"],
        ["🎫 REDEEM", "👥 REFERRAL"],
        ["🎁 DAILY BONUS", "🏆 LEADERBOARD"],
    ]
    if is_admin:
        rows.append(["👑 ADMIN PANEL"])
    return _kb(rows, "Choose an option below 👇")


def category_menu(types):
    """Dynamic store categories — one button per distinct content type
    currently in the database. Admins can add ANY category name and it
    will automatically appear here."""
    rows = []
    buttons = [f"📦 {t.upper()}" for t in types]
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    if not rows:
        rows.append(["😴 NO CATEGORIES YET"])
    rows.append(["🛒 MY PURCHASES"])
    rows.append(["🔙 BACK TO MENU"])
    return _kb(rows, "Pick a category 👇")


def admin_menu():
    rows = [
        ["📊 STATS", "📦 ADD CONTENT"],
        ["📋 MANAGE CONTENT", "🎫 GIFT CODES"],
        ["➕ ADD COINS", "➖ REMOVE COINS"],
        ["👥 USERS", "📢 BROADCAST"],
        ["🚫 BAN USER", "✅ UNBAN USER"],
        ["🔙 BACK TO MENU"],
    ]
    return _kb(rows, "Admin tools 👑")


def cancel_menu(placeholder="Type your input, or tap ❌ CANCEL"):
    return _kb([["❌ CANCEL"]], placeholder)


def confirm_menu(yes_text="✅ CONFIRM", no_text="❌ CANCEL"):
    """Generic yes/no confirmation keyboard — handy for anything that
    should double-check before acting."""
    return _kb([[yes_text, no_text]], "Please confirm 👇")


def back_to_store():
    return _kb([["🔙 BACK TO MENU"]], "Type the ID number to buy")


def join_gate_menu():
    """Shown when a user hasn't joined the mandatory channel yet."""
    return _kb([["✅ I'VE JOINED"]], "Tap once you've joined the channel")
