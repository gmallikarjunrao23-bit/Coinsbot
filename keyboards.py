"""
Reply keyboard layouts. No inline buttons anywhere — pure ReplyKeyboardMarkup,
but each menu has its own distinct visual "skin" (different emoji border style)
so navigating the bot feels premium and varied.
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu(is_admin: bool):
    rows = [
        ["🏪 STORE", "👤 PROFILE"],
        ["🎫 REDEEM", "👥 REFERRAL"],
        ["🎁 DAILY BONUS", "🏆 LEADERBOARD"],
        ["📢 CHANNEL"],
    ]
    if is_admin:
        rows.append(["👑 ADMIN PANEL"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def store_menu():
    rows = [
        ["📚 COURSES", "📁 FILES"],
        ["🔧 METHODS", "🛒 MY PURCHASES"],
        ["🔙 BACK TO MENU"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu():
    rows = [
        ["📊 STATS", "📦 ADD CONTENT"],
        ["📋 MANAGE CONTENT", "🎫 GIFT CODES"],
        ["💰 ADD COINS", "👥 USERS"],
        ["📢 BROADCAST", "🚫 BAN"],
        ["🔙 BACK TO MENU"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def giftcode_menu():
    rows = [
        ["🎫 SINGLE CODE", "📦 BULK CODES"],
        ["🔙 BACK TO ADMIN"],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def cancel_menu():
    return ReplyKeyboardMarkup([["❌ CANCEL"]], resize_keyboard=True)


def back_to_store():
    return ReplyKeyboardMarkup([["🔙 BACK TO MENU"]], resize_keyboard=True)

