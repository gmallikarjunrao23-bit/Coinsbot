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
        ["📢 CHANNEL"],
    ]
    if is_admin:
        rows.append(["👑 ADMIN PANEL"])
    return _kb(rows, "Choose an option below 👇")


def store_menu():
    rows = [
        ["📚 COURSES", "📁 FILES"],
        ["🔧 METHODS", "🛒 MY PURCHASES"],
        ["🔙 BACK TO MENU"],
    ]
    return _kb(rows, "Pick a category 👇")


def admin_menu():
    rows = [
        ["📊 STATS", "📦 ADD CONTENT"],
        ["📋 MANAGE CONTENT", "🎫 GIFT CODES"],
        ["💰 ADD COINS", "👥 USERS"],
        ["📢 BROADCAST", "🚫 BAN"],
        ["🔙 BACK TO MENU"],
    ]
    return _kb(rows, "Admin tools 👑")


def giftcode_menu():
    rows = [
        ["🎫 SINGLE CODE", "📦 BULK CODES"],
        ["🔙 BACK TO ADMIN"],
    ]
    return _kb(rows, "Generate a code 👇")


def cancel_menu(placeholder="Type your input, or tap ❌ CANCEL"):
    return _kb([["❌ CANCEL"]], placeholder)


def confirm_menu(yes_text="✅ CONFIRM", no_text="❌ CANCEL"):
    """Generic yes/no confirmation keyboard — handy for anything that
    should double-check before acting (e.g. a costly purchase, a
    destructive admin action, or a broadcast about to go out)."""
    return _kb([[yes_text, no_text]], "Please confirm 👇")


def back_to_store():
    return _kb([["🔙 BACK TO MENU"]], "Send /buy <id> to purchase")
