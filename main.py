"""
Premium Content Marketplace Bot
--------------------------------
A Telegram bot where users earn coins via referrals & daily bonuses,
then spend coins on premium content (courses / files / methods).

Owner: @DEVILHASHJ
"""
import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN, FOOTER, is_admin, REFERRAL_BONUS,
    DAILY_BONUS_AMOUNT, CONTENT_TYPES,
)
from database import Database
import keyboards as kb

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = Database()

TYPE_EMOJI = {"course": "📚", "file": "📁", "method": "🔧"}
TYPE_LABEL = {"course": "COURSE", "file": "FILE", "method": "METHOD"}


# =========================================================
#                     HELPER FUNCTIONS
# =========================================================
def fmt_coins(n):
    return f"{n:,} 🪙"


async def send_main_menu(update: Update, text: str):
    user_id = update.effective_user.id
    await update.message.reply_text(
        text + FOOTER,
        reply_markup=kb.main_menu(is_admin(user_id)),
        parse_mode="Markdown",
    )


def clear_awaiting(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting", None)
    context.user_data.pop("temp", None)


# =========================================================
#                     /start COMMAND
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    existing = db.get_user(user.id)
    is_new = existing is None

    referred_by = 0
    if is_new and args:
        arg = args[0]
        if arg.startswith("ref_"):
            try:
                ref_id = int(arg.replace("ref_", ""))
                if ref_id != user.id and db.get_user(ref_id):
                    referred_by = ref_id
            except ValueError:
                pass

    if is_new:
        db.create_user(user.id, user.username, user.first_name, referred_by)
        if referred_by:
            db.apply_referral(user.id, referred_by)

    db.touch_last_active(user.id)
    u = db.get_user(user.id)

    if u["banned"]:
        await update.message.reply_text(
            "🚫 *You are banned from using this bot.*\n\n"
            f"Contact {FOOTER}", parse_mode="Markdown"
        )
        return

    welcome = (
        "✨━━━━━━━━━━━━━━━✨\n"
        "   💎 *PREMIUM CONTENT HUB* 💎\n"
        "✨━━━━━━━━━━━━━━━✨\n\n"
        f"👋 Welcome, *{user.first_name}*!\n\n"
        f"🪙 *Balance:* {fmt_coins(u['coins'])}\n"
        f"👥 *Referrals:* {u['referral_count']}\n\n"
        "Use the menu below to explore the store, earn coins, "
        "and unlock premium courses, files & methods 🚀"
    )
    await send_main_menu(update, welcome)


# =========================================================
#                     PROFILE
# =========================================================
async def show_profile(update: Update):
    user = update.effective_user
    u = db.get_user(user.id)
    created = u["created_at"][:10] if u["created_at"] else "-"
    text = (
        "🌟━━━━━━━━━━━━━━━🌟\n"
        "      👤 *YOUR PROFILE*\n"
        "🌟━━━━━━━━━━━━━━━🌟\n\n"
        f"🆔 *User ID:* `{u['user_id']}`\n"
        f"📛 *Name:* {u['first_name']}\n"
        f"🔖 *Username:* @{u['username'] if u['username'] else 'N/A'}\n"
        f"🪙 *Coin Balance:* {fmt_coins(u['coins'])}\n"
        f"👥 *Total Referrals:* {u['referral_count']}\n"
        f"💸 *Total Spent:* {fmt_coins(u['total_spent'])}\n"
        f"📅 *Joined:* {created}\n"
    )
    await update.message.reply_text(text + FOOTER, parse_mode="Markdown")


# =========================================================
#                     REFERRAL
# =========================================================
async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    text = (
        "🔗━━━━━━━━━━━━━━━🔗\n"
        "     👥 *REFERRAL PROGRAM*\n"
        "🔗━━━━━━━━━━━━━━━🔗\n\n"
        f"🎁 Earn *{REFERRAL_BONUS} coins* for every friend who joins!\n"
        f"🎁 Your friend also gets *{REFERRAL_BONUS} coins* instantly!\n\n"
        f"📎 *Your Referral Link:*\n`{link}`\n\n"
        f"👥 *Total Referrals:* {u['referral_count']}\n"
        f"💰 *Coins Earned From Referrals:* {u['referral_count'] * REFERRAL_BONUS}"
    )
    await update.message.reply_text(text + FOOTER, parse_mode="Markdown")


# =========================================================
#                     DAILY BONUS
# =========================================================
async def claim_daily_bonus(update: Update):
    user_id = update.effective_user.id
    if db.can_claim_daily(user_id):
        db.claim_daily(user_id, DAILY_BONUS_AMOUNT)
        u = db.get_user(user_id)
        text = (
            "🎁━━━━━━━━━━━━━━━🎁\n"
            f"🎉 You claimed *{DAILY_BONUS_AMOUNT} coins!*\n"
            "⏰ Come back tomorrow for more!\n"
            "🎁━━━━━━━━━━━━━━━🎁\n\n"
            f"🪙 *New Balance:* {fmt_coins(u['coins'])}"
        )
    else:
        text = (
            "⏳ *Already Claimed!*\n\n"
            "You've already claimed your daily bonus today.\n"
            "Come back after 24 hours ⏰"
        )
    await update.message.reply_text(text + FOOTER, parse_mode="Markdown")


# =========================================================
#                     LEADERBOARD
# =========================================================
async def show_leaderboard(update: Update):
    top = db.get_leaderboard(10)
    medals = ["🥇", "🥈", "🥉"]
    lines = [
        "🏆━━━━━━━━━━━━━━━🏆",
        "     🏆 *TOP 10 LEADERBOARD*",
        "🏆━━━━━━━━━━━━━━━🏆\n",
    ]
    if not top:
        lines.append("No users yet. Be the first! 🚀")
    for i, u in enumerate(top):
        badge = medals[i] if i < 3 else f"{i+1}."
        uname = u["username"] if u["username"] else u["first_name"]
        lines.append(f"{badge} *{uname}* — {fmt_coins(u['coins'])}")
    await update.message.reply_text("\n".join(lines) + FOOTER, parse_mode="Markdown")


# =========================================================
#                     CHANNEL
# =========================================================
async def show_channel(update: Update):
    from config import CHANNEL_LINK
    text = (
        "📢━━━━━━━━━━━━━━━📢\n"
        "   📢 *OFFICIAL CHANNEL*\n"
        "📢━━━━━━━━━━━━━━━📢\n\n"
        f"Join our channel for updates, drops & offers:\n{CHANNEL_LINK}"
    )
    await update.message.reply_text(text + FOOTER, parse_mode="Markdown")


# =========================================================
#                     STORE
# =========================================================
async def show_store(update: Update):
    text = (
        "🏪━━━━━━━━━━━━━━━🏪\n"
        "     💎 *PREMIUM STORE* 💎\n"
        "🏪━━━━━━━━━━━━━━━🏪\n\n"
        "📚 *Courses* — Learn from premium material\n"
        "📁 *Files* — Download exclusive files\n"
        "🔧 *Methods* — Proven guides & strategies\n\n"
        "👇 Pick a category below:"
    )
    await update.message.reply_text(text + FOOTER, reply_markup=kb.store_menu(), parse_mode="Markdown")


async def show_content_list(update: Update, ctype: str):
    items = db.get_content_by_type(ctype)
    emoji = TYPE_EMOJI[ctype]
    label = TYPE_LABEL[ctype]
    lines = [
        f"{emoji}━━━━━━━━━━━━━━━{emoji}",
        f"      {emoji} *{label}S* {emoji}",
        f"{emoji}━━━━━━━━━━━━━━━{emoji}\n",
    ]
    if not items:
        lines.append(f"No {ctype}s available right now. Check back soon! ⏳")
    else:
        for it in items:
            lines.append(
                f"🆔 `{it['id']}` | *{it['title']}*\n"
                f"📝 {it['description']}\n"
                f"🪙 Price: {fmt_coins(it['price'])} | 🔥 Sold: {it['total_sold']}\n"
                f"👉 To buy, send: `/buy {it['id']}`\n"
            )
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.back_to_store(), parse_mode="Markdown"
    )


async def show_my_purchases(update: Update):
    user_id = update.effective_user.id
    purchases = db.get_purchases(user_id)
    lines = [
        "🛒━━━━━━━━━━━━━━━🛒",
        "     🛒 *MY PURCHASES*",
        "🛒━━━━━━━━━━━━━━━🛒\n",
    ]
    if not purchases:
        lines.append("You haven't purchased anything yet. Visit the 🏪 STORE!")
    else:
        for p in purchases:
            date = p["purchased_at"][:10]
            lines.append(
                f"📦 *{p['title'] or 'Deleted Content'}*\n"
                f"🪙 Paid: {fmt_coins(p['price'])} | 📅 {date}\n"
            )
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.store_menu(), parse_mode="Markdown"
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/buy <content_id>`", parse_mode="Markdown")
        return
    try:
        content_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid content ID.")
        return

    item = db.get_content_by_id(content_id)
    if not item or not item["active"]:
        await update.message.reply_text("⚠️ Content not found or no longer available.")
        return

    u = db.get_user(user_id)
    if u["coins"] < item["price"]:
        await update.message.reply_text(
            f"❌ *Insufficient Coins!*\n\n"
            f"🪙 Required: {fmt_coins(item['price'])}\n"
            f"🪙 Your Balance: {fmt_coins(u['coins'])}\n\n"
            "Earn more via 🎁 DAILY BONUS or 👥 REFERRAL!",
            parse_mode="Markdown",
        )
        return

    db.update_coins(user_id, -item["price"], "purchase", f"Bought content #{content_id}")
    db.record_purchase(user_id, content_id, item["type"], item["price"])
    db.increment_sold(content_id)

    await update.message.reply_text(
        "✅━━━━━━━━━━━━━━━✅\n"
        "   🎉 *PURCHASE SUCCESSFUL!* 🎉\n"
        "✅━━━━━━━━━━━━━━━✅\n\n"
        f"📦 *{item['title']}*\n"
        f"🪙 Paid: {fmt_coins(item['price'])}\n"
        f"📄 File Name: `{item['file_name']}`",
        parse_mode="Markdown",
    )
    if item["file_id"]:
        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=item["file_id"],
                filename=item["file_name"] or None,
                caption=f"📦 {item['title']}" + FOOTER,
            )
        except Exception:
            await update.message.reply_text(
                f"📎 *File ID:* `{item['file_id']}`\n(Forward this ID to the bot owner if it doesn't open.)",
                parse_mode="Markdown",
            )


# =========================================================
#                     REDEEM GIFT CODE
# =========================================================
async def redeem_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "redeem_code"
    await update.message.reply_text(
        "🎫━━━━━━━━━━━━━━━🎫\n"
        "   🎫 *REDEEM GIFT CODE*\n"
        "🎫━━━━━━━━━━━━━━━🎫\n\n"
        "Please send your 10-character gift code now 👇",
        reply_markup=kb.cancel_menu(),
        parse_mode="Markdown",
    )


async def redeem_process(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    user_id = update.effective_user.id
    coins, status = db.redeem_gift_code(code.strip().upper(), user_id)
    clear_awaiting(context)
    if status == "ok":
        u = db.get_user(user_id)
        text = (
            "✅ *Code Redeemed Successfully!*\n\n"
            f"🪙 +{coins} coins added!\n"
            f"🪙 New Balance: {fmt_coins(u['coins'])}"
        )
    elif status == "used":
        text = "⚠️ This code has already been used."
    else:
        text = "❌ Invalid gift code. Please check and try again."
    await send_main_menu(update, text)


# =========================================================
#                     ADMIN: STATS
# =========================================================
async def admin_stats(update: Update):
    s = db.get_stats()
    text = (
        "📊━━━━━━━━━━━━━━━📊\n"
        "      📊 *BOT STATISTICS*\n"
        "📊━━━━━━━━━━━━━━━📊\n\n"
        f"👥 Total Users: *{s['total_users']}*\n"
        f"🪙 Total Coins in Circulation: *{s['total_coins']}*\n"
        f"📦 Total Content Items: *{s['total_content']}*\n"
        f"🛒 Total Sales: *{s['total_sales']}*\n"
        f"🆕 New Users Today: *{s['new_today']}*\n"
        f"🟢 Active Today: *{s['active_today']}*"
    )
    await update.message.reply_text(text + FOOTER, reply_markup=kb.admin_menu(), parse_mode="Markdown")


# =========================================================
#                     ADMIN: ADD CONTENT
# =========================================================
async def admin_add_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "add_content"
    await update.message.reply_text(
        "📦━━━━━━━━━━━━━━━📦\n"
        "   📦 *ADD NEW CONTENT*\n"
        "📦━━━━━━━━━━━━━━━📦\n\n"
        "Send content in this exact format:\n\n"
        "`Title|Description|Type|Price|FileID|FileName`\n\n"
        "Type must be one of: `course`, `file`, `method`\n\n"
        "*Example:*\n"
        "`Python Mastery|Full Python course|course|50|BQACAgIAAx...|python.pdf`",
        reply_markup=kb.cancel_menu(),
        parse_mode="Markdown",
    )


async def admin_add_content_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    parts = text.split("|")
    clear_awaiting(context)
    if len(parts) != 6:
        await update.message.reply_text(
            "⚠️ Invalid format. Please use exactly 6 fields separated by `|`.",
            reply_markup=kb.admin_menu(), parse_mode="Markdown",
        )
        return
    title, desc, ctype, price, file_id, file_name = [p.strip() for p in parts]
    ctype = ctype.lower()
    if ctype not in CONTENT_TYPES:
        await update.message.reply_text(
            "⚠️ Type must be `course`, `file`, or `method`.",
            reply_markup=kb.admin_menu(), parse_mode="Markdown",
        )
        return
    try:
        price = int(price)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Price must be a number.", reply_markup=kb.admin_menu()
        )
        return

    content_id = db.add_content(title, desc, ctype, price, file_id, file_name)
    await update.message.reply_text(
        f"✅ Content added successfully! (ID: `{content_id}`)",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


async def admin_manage_content(update: Update):
    items = db.get_all_content()
    lines = [
        "📋━━━━━━━━━━━━━━━📋",
        "     📋 *MANAGE CONTENT*",
        "📋━━━━━━━━━━━━━━━📋\n",
    ]
    if not items:
        lines.append("No content added yet.")
    for it in items:
        status = "🟢 Active" if it["active"] else "🔴 Inactive"
        lines.append(
            f"🆔 `{it['id']}` | *{it['title']}* ({it['type']})\n"
            f"🪙 {it['price']} | 🔥 Sold: {it['total_sold']} | {status}\n"
        )
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.admin_menu(), parse_mode="Markdown"
    )


# =========================================================
#                     ADMIN: GIFT CODES
# =========================================================
async def admin_giftcodes_menu(update: Update):
    await update.message.reply_text(
        "🎫━━━━━━━━━━━━━━━🎫\n"
        "     🎫 *GIFT CODE MANAGER*\n"
        "🎫━━━━━━━━━━━━━━━🎫\n\n"
        "Generate a single code, or bulk-generate many at once.",
        reply_markup=kb.giftcode_menu(), parse_mode="Markdown",
    )


async def admin_giftcode_single_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "gift_single"
    await update.message.reply_text(
        "Send the coin amount for this gift code (e.g. `50`):",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_giftcode_single_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    try:
        amount = int(text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Please send a valid number.", reply_markup=kb.giftcode_menu())
        return
    code = db.generate_gift_code(amount, update.effective_user.id)
    await update.message.reply_text(
        f"✅ *Gift Code Generated!*\n\n🎫 Code: `{code}`\n🪙 Value: {amount} coins",
        reply_markup=kb.giftcode_menu(), parse_mode="Markdown",
    )


async def admin_giftcode_bulk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "gift_bulk"
    await update.message.reply_text(
        "Send `amount,count` to bulk generate codes.\n\n*Example:* `50,10` → 10 codes worth 50 coins each",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_giftcode_bulk_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    try:
        amount_str, count_str = text.split(",")
        amount, count = int(amount_str.strip()), int(count_str.strip())
        count = min(count, 100)  # safety cap
    except (ValueError, IndexError):
        await update.message.reply_text(
            "⚠️ Invalid format. Use `amount,count` e.g. `50,10`",
            reply_markup=kb.giftcode_menu(), parse_mode="Markdown",
        )
        return
    codes = [db.generate_gift_code(amount, update.effective_user.id) for _ in range(count)]
    codes_text = "\n".join(f"`{c}`" for c in codes)
    await update.message.reply_text(
        f"✅ *{count} Gift Codes Generated!* (🪙 {amount} each)\n\n{codes_text}",
        reply_markup=kb.giftcode_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     ADMIN: ADD COINS
# =========================================================
async def admin_add_coins_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "add_coins"
    await update.message.reply_text(
        "💰━━━━━━━━━━━━━━━💰\n"
        "     💰 *ADD COINS*\n"
        "💰━━━━━━━━━━━━━━━💰\n\n"
        "Send `user_id,amount` — e.g. `123456789,100`",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_add_coins_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    try:
        uid_str, amt_str = text.split(",")
        uid, amt = int(uid_str.strip()), int(amt_str.strip())
    except (ValueError, IndexError):
        await update.message.reply_text(
            "⚠️ Invalid format. Use `user_id,amount`",
            reply_markup=kb.admin_menu(), parse_mode="Markdown",
        )
        return
    target = db.get_user(uid)
    if not target:
        await update.message.reply_text("⚠️ User not found.", reply_markup=kb.admin_menu())
        return
    db.update_coins(uid, amt, "admin_add", "Coins added by admin")
    await update.message.reply_text(
        f"✅ Added {amt} coins to user `{uid}`.",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     ADMIN: USERS
# =========================================================
async def admin_users(update: Update):
    users = db.get_all_users()[:30]
    lines = [
        "👥━━━━━━━━━━━━━━━👥",
        "      👥 *ALL USERS*",
        "👥━━━━━━━━━━━━━━━👥\n",
        f"(showing latest {len(users)})\n",
    ]
    for u in users:
        ban = "🚫" if u["banned"] else "✅"
        lines.append(f"{ban} `{u['user_id']}` — {u['first_name']} | 🪙 {u['coins']}")
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.admin_menu(), parse_mode="Markdown"
    )


# =========================================================
#                     ADMIN: BROADCAST
# =========================================================
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "broadcast"
    await update.message.reply_text(
        "📢 Send the message you want to broadcast to *all users*:",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    users = db.get_all_users()
    sent, failed = 0, 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 *Announcement*\n\n{text}" + FOOTER,
                parse_mode="Markdown",
            )
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"✅ Broadcast complete!\n📨 Sent: {sent} | ❌ Failed: {failed}",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     ADMIN: BAN
# =========================================================
async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "ban"
    await update.message.reply_text(
        "🚫 Send the `user_id` to toggle ban/unban:",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_ban_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    try:
        uid = int(text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.", reply_markup=kb.admin_menu())
        return
    target = db.get_user(uid)
    if not target:
        await update.message.reply_text("⚠️ User not found.", reply_markup=kb.admin_menu())
        return
    new_status = not bool(target["banned"])
    db.set_ban(uid, new_status)
    status_text = "🚫 Banned" if new_status else "✅ Unbanned"
    await update.message.reply_text(
        f"User `{uid}` is now: *{status_text}*",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     CANCEL / BACK HANDLERS
# =========================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_awaiting(context)
    await send_main_menu(update, "❌ Action cancelled.")


# =========================================================
#                     MAIN TEXT ROUTER
# =========================================================
AWAITING_HANDLERS = {
    "redeem_code": redeem_process,
    "add_content": admin_add_content_process,
    "gift_single": admin_giftcode_single_process,
    "gift_bulk": admin_giftcode_bulk_process,
    "add_coins": admin_add_coins_process,
    "broadcast": admin_broadcast_process,
    "ban": admin_ban_process,
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # Ensure user exists (in case /start was skipped)
    if not db.get_user(user.id):
        db.create_user(user.id, user.username, user.first_name)
    db.touch_last_active(user.id)

    if db.is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    # Cancel button always works
    if text == "❌ CANCEL":
        await cancel(update, context)
        return

    # Handle pending "awaiting" input first
    awaiting = context.user_data.get("awaiting")
    if awaiting and awaiting in AWAITING_HANDLERS:
        await AWAITING_HANDLERS[awaiting](update, context, text)
        return

    # ---------------- MAIN MENU ----------------
    if text == "🏪 STORE":
        await show_store(update)
    elif text == "👤 PROFILE":
        await show_profile(update)
    elif text == "🎫 REDEEM":
        await redeem_start(update, context)
    elif text == "👥 REFERRAL":
        await show_referral(update, context)
    elif text == "🎁 DAILY BONUS":
        await claim_daily_bonus(update)
    elif text == "🏆 LEADERBOARD":
        await show_leaderboard(update)
    elif text == "📢 CHANNEL":
        await show_channel(update)
    elif text == "👑 ADMIN PANEL":
        if is_admin(user.id):
            await update.message.reply_text(
                "👑━━━━━━━━━━━━━━━👑\n"
                "     👑 *ADMIN CONTROL PANEL*\n"
                "👑━━━━━━━━━━━━━━━👑",
                reply_markup=kb.admin_menu(), parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("⛔ You are not authorized.")

    # ---------------- STORE MENU ----------------
    elif text == "📚 COURSES":
        await show_content_list(update, "course")
    elif text == "📁 FILES":
        await show_content_list(update, "file")
    elif text == "🔧 METHODS":
        await show_content_list(update, "method")
    elif text == "🛒 MY PURCHASES":
        await show_my_purchases(update)
    elif text == "🔙 BACK TO MENU":
        await send_main_menu(update, "🏠 Main Menu")

    # ---------------- ADMIN MENU ----------------
    elif text == "📊 STATS" and is_admin(user.id):
        await admin_stats(update)
    elif text == "📦 ADD CONTENT" and is_admin(user.id):
        await admin_add_content_start(update, context)
    elif text == "📋 MANAGE CONTENT" and is_admin(user.id):
        await admin_manage_content(update)
    elif text == "🎫 GIFT CODES" and is_admin(user.id):
        await admin_giftcodes_menu(update)
    elif text == "💰 ADD COINS" and is_admin(user.id):
        await admin_add_coins_start(update, context)
    elif text == "👥 USERS" and is_admin(user.id):
        await admin_users(update)
    elif text == "📢 BROADCAST" and is_admin(user.id):
        await admin_broadcast_start(update, context)
    elif text == "🚫 BAN" and is_admin(user.id):
        await admin_ban_start(update, context)
    elif text == "🔙 BACK TO ADMIN" and is_admin(user.id):
        await update.message.reply_text(
            "👑 *ADMIN CONTROL PANEL*", reply_markup=kb.admin_menu(), parse_mode="Markdown"
        )

    # ---------------- GIFT CODE SUBMENU ----------------
    elif text == "🎫 SINGLE CODE" and is_admin(user.id):
        await admin_giftcode_single_start(update, context)
    elif text == "📦 BULK CODES" and is_admin(user.id):
        await admin_giftcode_bulk_start(update, context)

    else:
        await update.message.reply_text(
            "❓ I didn't understand that. Please use the menu buttons below 👇",
            reply_markup=kb.main_menu(is_admin(user.id)),
        )


# =========================================================
#                     ERROR HANDLER
# =========================================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


# =========================================================
#                     MAIN ENTRYPOINT
# =========================================================
def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Please configure your .env file.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_error_handler(error_handler)

    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
