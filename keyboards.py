"""
Reply keyboard layouts. No inline buttons anywhere — pure ReplyKeyboardMarkup.
Labels use Title Case with a single leading icon (not ALL CAPS, not stacked
emoji) for a cleaner, more professional feel.
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
        ["🏪 Store", "👤 Profile"],
        ["🎫 Redeem Code", "👥 Referrals"],
        ["🎁 Daily Bonus", "🏆 Leaderboard"],
    ]
    if is_admin:
        rows.append(["👑 Admin Panel"])
    return _kb(rows, "Choose an option")


def category_menu(buttons):
    """`buttons` is a list of ready-made labels (e.g. '📖 Ebook') so the
    caller can assign a smart icon per category."""
    rows = []
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    if not rows:
        rows.append(["No categories yet"])
    rows.append(["🛒 My Purchases"])
    rows.append(["🔙 Back"])
    return _kb(rows, "Select a category")


def admin_menu():
    rows = [
        ["📊 Stats", "📦 Add Content"],
        ["📋 Manage Content", "🎫 Gift Codes"],
        ["➕ Add Coins", "➖ Remove Coins"],
        ["👥 Users", "📢 Broadcast"],
        ["🚫 Ban User", "✅ Unban User"],
        ["🔙 Back"],
    ]
    return _kb(rows, "Admin tools")


def cancel_menu(placeholder="Type your response, or tap Cancel"):
    return _kb([["❌ Cancel"]], placeholder)


def confirm_menu(yes_text="✅ Confirm", no_text="❌ Cancel"):
    """Generic yes/no confirmation keyboard — handy for anything that
    should double-check before acting."""
    return _kb([[yes_text, no_text]], "Please confirm")


def back_to_store():
    return _kb([["🔙 Back"]], "Type the item number to purchase")


def join_gate_menu():
    """Shown when a user hasn't joined the mandatory channel yet."""
    return _kb([["✅ I've Joined"]], "Tap once you've joined the channel")
