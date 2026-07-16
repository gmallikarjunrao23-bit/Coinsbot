"""
Premium Content Marketplace Bot
--------------------------------
A Telegram bot where users earn coins via referrals & daily bonuses,
then spend coins on premium content of ANY category (courses, files,
ebooks, scripts, templates — anything an admin adds).

Owner: @DEVILHASHJ
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, FOOTER, is_admin, REFERRAL_BONUS, DAILY_BONUS_AMOUNT, CHANNEL_LINK, CHANNEL_ID
from database import Database
import keyboards as kb

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = Database()


# =========================================================
#                     HELPER FUNCTIONS
# =========================================================
def fmt_coins(n):
    return f"{n:,} 🪙"


def fmt_date(dt):
    """Postgres returns native datetime objects (not strings), so format
    them safely here instead of string-slicing them."""
    if not dt:
        return "-"
    try:
        return dt.strftime("%Y-%m-%d")
    except AttributeError:
        return str(dt)[:10]


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


async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Checks channel membership for the mandatory join-gate.
    If CHANNEL_ID isn't configured, the gate is disabled (always passes)."""
    if not CHANNEL_ID:
        logger.info("Join-gate check skipped — CHANNEL_ID is not set.")
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        result = member.status in ("member", "administrator", "creator")
        logger.info(
            f"Join-gate check: user={user_id} channel={CHANNEL_ID} "
            f"status={member.status} allowed={result}"
        )
        return result
    except Exception as e:
        logger.warning(f"Join-gate check FAILED for user={user_id} channel={CHANNEL_ID}: {e}")
        return False


async def send_join_gate(update: Update):
    text = (
        "🔒━━━━━━━━━━━━━━━🔒\n"
        "     🔒 *ACCESS RESTRICTED*\n"
        "🔒━━━━━━━━━━━━━━━🔒\n\n"
        "To use this bot, you must first join our official channel 👇\n\n"
        f"📢 {CHANNEL_LINK}\n\n"
        "Once you've joined, tap *✅ I'VE JOINED* below to unlock the bot."
    )
    await update.message.reply_text(text, reply_markup=kb.join_gate_menu(), parse_mode="Markdown")


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
            try:
                referrer = db.get_user(referred_by)
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=(
                        "🎉━━━━━━━━━━━━━━━🎉\n"
                        "     🎉 *NEW REFERRAL!*\n"
                        "🎉━━━━━━━━━━━━━━━🎉\n\n"
                        f"👤 *{user.first_name}* joined using your referral link!\n"
                        f"🪙 +{REFERRAL_BONUS} coins added!\n"
                        f"🪙 New Balance: {fmt_coins(referrer['coins'])}" + FOOTER
                    ),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Could not notify referrer {referred_by}: {e}")

    db.touch_last_active(user.id)
    u = db.get_user(user.id)

    if u["banned"]:
        await update.message.reply_text(
            "🚫 *You are banned from using this bot.*" + FOOTER, parse_mode="Markdown"
        )
        return

    if not await is_subscribed(context, user.id):
        await send_join_gate(update)
        return

    welcome = (
        "✨━━━━━━━━━━━━━━━✨\n"
        "   💎 *PREMIUM CONTENT HUB* 💎\n"
        "✨━━━━━━━━━━━━━━━✨\n\n"
        f"👋 Welcome, *{user.first_name}*!\n\n"
        f"🪙 *Balance:* {fmt_coins(u['coins'])}\n"
        f"👥 *Referrals:* {u['referral_count']}\n\n"
        "Use the menu below to explore the store, earn coins, "
        "and unlock premium content 🚀"
    )
    await send_main_menu(update, welcome)


# =========================================================
#                     PROFILE  (fixed date formatting)
# =========================================================
async def show_profile(update: Update):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        await update.message.reply_text("⚠️ Profile not found. Please send /start first.")
        return
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
        f"📅 *Joined:* {fmt_date(u['created_at'])}\n"
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
        f"💰 *Coins Earned From Referrals:* {u['referral_count'] * REFERRAL_BONUS}\n\n"
        "You'll get an instant notification here whenever someone joins "
        "using your link! 🔔"
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
#                     STORE  (dynamic categories)
# =========================================================
async def show_store(update: Update):
    types = db.get_distinct_types()
    text = (
        "🏪━━━━━━━━━━━━━━━🏪\n"
        "     💎 *PREMIUM STORE* 💎\n"
        "🏪━━━━━━━━━━━━━━━🏪\n\n"
        "Browse everything available right now — pick a category below:"
    )
    await update.message.reply_text(text + FOOTER, reply_markup=kb.category_menu(types), parse_mode="Markdown")


async def show_content_list(update: Update, ctype: str):
    items = db.get_content_by_type(ctype)
    lines = [
        "📦━━━━━━━━━━━━━━━📦",
        f"      📦 *{ctype.upper()}* 📦",
        "📦━━━━━━━━━━━━━━━📦\n",
    ]
    if not items:
        lines.append("No items available in this category right now.")
    else:
        for it in items:
            lines.append(
                f"🆔 `{it['id']}` | *{it['title']}*\n"
                f"📝 {it['description']}\n"
                f"🪙 Price: {fmt_coins(it['price'])} | 🔥 Sold: {it['total_sold']}\n"
                f"👉 To buy, just type: `{it['id']}`\n"
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
            lines.append(
                f"📦 *{p['title'] or 'Deleted Content'}*\n"
                f"🪙 Paid: {fmt_coins(p['price'])} | 📅 {fmt_date(p['purchased_at'])}\n"
            )
    types = db.get_distinct_types()
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.category_menu(types), parse_mode="Markdown"
    )


async def perform_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, item: dict):
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

    db.update_coins(user_id, -item["price"], "purchase", f"Bought content #{item['id']}")
    db.record_purchase(user_id, item["id"], item["type"], item["price"])
    db.increment_sold(item["id"])

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
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=item["file_id"],
                    caption=f"📦 {item['title']}" + FOOTER,
                )
            except Exception:
                await update.message.reply_text(
                    f"📎 *File ID:* `{item['file_id']}`\n(Forward this to the bot owner if it doesn't open.)",
                    parse_mode="Markdown",
                )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(context, user_id):
        await send_join_gate(update)
        return
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

    await perform_purchase(update, context, user_id, item)


async def confirm_buy_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    temp = context.user_data.get("temp", {})
    content_id = temp.get("buy_content_id")
    clear_awaiting(context)
    if text != "✅ BUY NOW" or not content_id:
        await send_main_menu(update, "❌ Purchase cancelled.")
        return
    item = db.get_content_by_id(content_id)
    if not item or not item["active"]:
        await update.message.reply_text("⚠️ This item is no longer available.")
        return
    await perform_purchase(update, context, update.effective_user.id, item)


# =========================================================
#                     REDEEM GIFT CODE
# =========================================================
async def redeem_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "redeem_code"
    await update.message.reply_text(
        "🎫━━━━━━━━━━━━━━━🎫\n"
        "   🎫 *REDEEM GIFT CODE*\n"
        "🎫━━━━━━━━━━━━━━━🎫\n\n"
        "Please send your gift code now 👇",
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
    elif status == "already_redeemed":
        text = "⚠️ You've already redeemed this code before."
    elif status == "exhausted":
        text = "⚠️ This code has reached its maximum number of redemptions."
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
#         ADMIN: ADD CONTENT — conversational, any category,
#         any file type, no rigid pipe-format required.
# =========================================================
async def admin_add_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "add_title"
    context.user_data["temp"] = {}
    await update.message.reply_text(
        "📦━━━━━━━━━━━━━━━📦\n"
        "   📦 *ADD NEW CONTENT*\n"
        "📦━━━━━━━━━━━━━━━📦\n\n"
        "*Step 1/5* — Send the *title*:",
        reply_markup=kb.cancel_menu(),
        parse_mode="Markdown",
    )


async def add_content_title(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    context.user_data["temp"]["title"] = text.strip()
    context.user_data["awaiting"] = "add_desc"
    await update.message.reply_text(
        "*Step 2/5* — Send the *description*:", reply_markup=kb.cancel_menu(), parse_mode="Markdown"
    )


async def add_content_desc(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    context.user_data["temp"]["description"] = text.strip()
    context.user_data["awaiting"] = "add_type"
    await update.message.reply_text(
        "*Step 3/5* — Send the *category* — this can be ANYTHING you like "
        "(e.g. `Ebook`, `Script`, `Course`, `Template`, `Wallpaper Pack`):",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def add_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    context.user_data["temp"]["type"] = text.strip().lower()
    context.user_data["awaiting"] = "add_price"
    await update.message.reply_text(
        "*Step 4/5* — Send the *price* in coins (numbers only):",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def add_content_price(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        price = int(text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Please send a valid whole number for the price.")
        return
    context.user_data["temp"]["price"] = price
    context.user_data["awaiting"] = "add_file"
    await update.message.reply_text(
        "*Step 5/5* — Now send the *actual file* — any document, PDF, ZIP, "
        "photo, video, or audio file works. Just attach and send it 📎",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


def _extract_file_info(message):
    """Pulls (file_id, file_name) from whatever kind of media was sent —
    accepts ANY content type: documents, photos, videos, audio, voice notes."""
    if message.document:
        return message.document.file_id, message.document.file_name or "file"
    if message.video:
        return message.video.file_id, getattr(message.video, "file_name", None) or "video.mp4"
    if message.audio:
        return message.audio.file_id, getattr(message.audio, "file_name", None) or "audio.mp3"
    if message.voice:
        return message.voice.file_id, "voice.ogg"
    if message.photo:
        return message.photo[-1].file_id, "photo.jpg"
    return None, None


async def admin_add_content_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the file admin sends as the final step of ADD CONTENT.
    Only acts when the admin is mid-flow and awaiting a file."""
    user = update.effective_user
    if not is_admin(user.id) or context.user_data.get("awaiting") != "add_file":
        return

    file_id, file_name = _extract_file_info(update.message)
    if not file_id:
        await update.message.reply_text(
            "⚠️ Please send a valid file (document, photo, video, or audio)."
        )
        return

    temp = context.user_data.get("temp", {})
    content_id = db.add_content(
        temp.get("title", "Untitled"),
        temp.get("description", ""),
        temp.get("type", "misc"),
        temp.get("price", 0),
        file_id,
        file_name,
    )
    clear_awaiting(context)
    await update.message.reply_text(
        f"✅ *Content added successfully!* (ID: `{content_id}`)\n\n"
        f"📦 {temp.get('title')}\n"
        f"🏷️ Category: {temp.get('type')}\n"
        f"🪙 Price: {temp.get('price')} coins",
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
    else:
        for it in items:
            status = "🟢 Active" if it["active"] else "🔴 Inactive"
            lines.append(
                f"🆔 `{it['id']}` | *{it['title']}* ({it['type']})\n"
                f"🪙 {it['price']} | 🔥 Sold: {it['total_sold']} | {status}\n"
            )
        lines.append("🗑️ To remove an item, send: `/remove <id>`")
    await update.message.reply_text(
        "\n".join(lines) + FOOTER, reply_markup=kb.admin_menu(), parse_mode="Markdown"
    )


async def remove_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/remove <content_id>`", parse_mode="Markdown")
        return
    try:
        content_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid content ID.")
        return
    deleted = db.delete_content(content_id)
    if deleted:
        await update.message.reply_text(
            f"🗑️ *Content #{content_id} removed successfully.*",
            reply_markup=kb.admin_menu(), parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "⚠️ Content not found — check the ID with 📋 MANAGE CONTENT.",
            reply_markup=kb.admin_menu(),
        )


# =========================================================
#                     ADMIN: GIFT CODES
# =========================================================
async def admin_giftcode_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "create_giftcode"
    await update.message.reply_text(
        "🎫━━━━━━━━━━━━━━━🎫\n"
        "   🎫 *CREATE GIFT CODE*\n"
        "🎫━━━━━━━━━━━━━━━🎫\n\n"
        "Send `coins,users` — e.g. `50,10`\n\n"
        "This creates *ONE* code worth *50 coins*, redeemable by *up to 10 "
        "different users* (each user can use it only once).\n\n"
        "For a code only one person can use, just set users to `1` — e.g. `50,1`",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_giftcode_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_awaiting(context)
    try:
        coins_str, users_str = text.split(",")
        coins, max_users = int(coins_str.strip()), int(users_str.strip())
        max_users = max(1, min(max_users, 10000))  # safety cap
    except (ValueError, IndexError):
        await update.message.reply_text(
            "⚠️ Invalid format. Use `coins,users` e.g. `50,10`",
            reply_markup=kb.admin_menu(), parse_mode="Markdown",
        )
        return
    code = db.generate_gift_code(coins, update.effective_user.id, max_users)
    await update.message.reply_text(
        f"✅ *Gift Code Created!*\n\n"
        f"🎫 Code: `{code}`\n"
        f"🪙 Coins per user: {coins}\n"
        f"👥 Max redemptions: {max_users}",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     ADMIN: ADD COINS
# =========================================================
async def admin_add_coins_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "add_coins"
    await update.message.reply_text(
        "➕━━━━━━━━━━━━━━━➕\n"
        "     ➕ *ADD COINS*\n"
        "➕━━━━━━━━━━━━━━━➕\n\n"
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
    new_balance = db.get_user(uid)["coins"]
    await update.message.reply_text(
        f"✅ Added {amt} coins to user `{uid}`.\n🪙 New balance: {new_balance}",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


async def admin_remove_coins_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "remove_coins"
    await update.message.reply_text(
        "➖━━━━━━━━━━━━━━━➖\n"
        "     ➖ *REMOVE COINS*\n"
        "➖━━━━━━━━━━━━━━━➖\n\n"
        "Send `user_id,amount` — e.g. `123456789,50`",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_remove_coins_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
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
    # Never let a balance go negative — clamp the deduction if needed.
    actual_deduction = min(amt, target["coins"])
    db.update_coins(uid, -actual_deduction, "admin_remove", "Coins removed by admin")
    new_balance = db.get_user(uid)["coins"]
    note = "" if actual_deduction == amt else f" (clamped from {amt}, balance can't go below 0)"
    await update.message.reply_text(
        f"✅ Removed {actual_deduction} coins from user `{uid}`{note}.\n🪙 New balance: {new_balance}",
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
        "🚫 Send the `user_id` to *ban*:",
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
    if target["banned"]:
        await update.message.reply_text(
            f"ℹ️ User `{uid}` is already banned.", reply_markup=kb.admin_menu(), parse_mode="Markdown"
        )
        return
    db.set_ban(uid, True)
    await update.message.reply_text(
        f"🚫 User `{uid}` has been *banned*.",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


async def admin_unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "unban"
    await update.message.reply_text(
        "✅ Send the `user_id` to *unban*:",
        reply_markup=kb.cancel_menu(), parse_mode="Markdown",
    )


async def admin_unban_process(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
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
    if not target["banned"]:
        await update.message.reply_text(
            f"ℹ️ User `{uid}` is not banned.", reply_markup=kb.admin_menu(), parse_mode="Markdown"
        )
        return
    db.set_ban(uid, False)
    await update.message.reply_text(
        f"✅ User `{uid}` has been *unbanned*.",
        reply_markup=kb.admin_menu(), parse_mode="Markdown",
    )


# =========================================================
#                     CANCEL
# =========================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_awaiting(context)
    await send_main_menu(update, "❌ Action cancelled.")


# =========================================================
#                     MAIN TEXT ROUTER
# =========================================================
AWAITING_HANDLERS = {
    "redeem_code": redeem_process,
    "add_title": add_content_title,
    "add_desc": add_content_desc,
    "add_type": add_content_type,
    "add_price": add_content_price,
    "confirm_buy": confirm_buy_process,
    "create_giftcode": admin_giftcode_process,
    "add_coins": admin_add_coins_process,
    "remove_coins": admin_remove_coins_process,
    "broadcast": admin_broadcast_process,
    "ban": admin_ban_process,
    "unban": admin_unban_process,
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if not db.get_user(user.id):
        db.create_user(user.id, user.username, user.first_name)
    db.touch_last_active(user.id)

    if db.is_banned(user.id):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    # Cancel always works, even mid-flow
    if text == "❌ CANCEL":
        await cancel(update, context)
        return

    # ---- Mandatory channel join gate ----
    if not await is_subscribed(context, user.id):
        await send_join_gate(update)
        return
    if text == "✅ I'VE JOINED":
        await send_main_menu(update, "✅ Thanks for joining! Welcome aboard 🎉")
        return

    # If admin is mid-way through the file step, remind them to send a file
    if context.user_data.get("awaiting") == "add_file":
        await update.message.reply_text(
            "📎 Please send the actual *file* now (document/photo/video/audio), or ❌ CANCEL.",
            parse_mode="Markdown",
        )
        return

    # Handle any other pending "awaiting" input
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
        await admin_giftcode_start(update, context)
    elif text == "➕ ADD COINS" and is_admin(user.id):
        await admin_add_coins_start(update, context)
    elif text == "➖ REMOVE COINS" and is_admin(user.id):
        await admin_remove_coins_start(update, context)
    elif text == "👥 USERS" and is_admin(user.id):
        await admin_users(update)
    elif text == "📢 BROADCAST" and is_admin(user.id):
        await admin_broadcast_start(update, context)
    elif text == "🚫 BAN USER" and is_admin(user.id):
        await admin_ban_start(update, context)
    elif text == "✅ UNBAN USER" and is_admin(user.id):
        await admin_unban_start(update, context)
    elif text == "🔙 BACK TO ADMIN" and is_admin(user.id):
        await update.message.reply_text(
            "👑 *ADMIN CONTROL PANEL*", reply_markup=kb.admin_menu(), parse_mode="Markdown"
        )

    # ---------------- GIFT CODE SUBMENU ----------------
    # (removed — 🎫 GIFT CODES now goes straight to the unified create flow)

    else:
        # ---------------- BUY BY ID (just type the number) ----------------
        if text.isdigit():
            content_id = int(text)
            item = db.get_content_by_id(content_id)
            if item and item["active"]:
                buyer = db.get_user(user.id)
                context.user_data["temp"] = {"buy_content_id": content_id}
                context.user_data["awaiting"] = "confirm_buy"
                confirm_text = (
                    "🛍️━━━━━━━━━━━━━━━🛍️\n"
                    "   🛍️ *CONFIRM PURCHASE*\n"
                    "🛍️━━━━━━━━━━━━━━━🛍️\n\n"
                    f"📦 *{item['title']}*\n"
                    f"📝 {item['description']}\n\n"
                    f"🪙 Price: {fmt_coins(item['price'])}\n"
                    f"🪙 Your Balance: {fmt_coins(buyer['coins'])}\n\n"
                    "Tap *✅ BUY NOW* to confirm, or *❌ CANCEL*."
                )
                await update.message.reply_text(
                    confirm_text, reply_markup=kb.confirm_menu("✅ BUY NOW", "❌ CANCEL"), parse_mode="Markdown"
                )
                return
            else:
                await update.message.reply_text("⚠️ No content found with that ID.")
                return

        # ---------------- DYNAMIC CONTENT CATEGORIES ----------------
        matched_category = None
        for t in db.get_distinct_types():
            if text == f"📦 {t.upper()}":
                matched_category = t
                break
        if matched_category:
            await show_content_list(update, matched_category)
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
        raise SystemExit("BOT_TOKEN is not set. Please configure your environment variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("remove", remove_content_command))
    app.add_handler(CommandHandler("cancel", cancel))
    # File uploads (any type) — only consumed when admin is mid ADD CONTENT flow
    app.add_handler(MessageHandler(
        (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE) & ~filters.COMMAND,
        admin_add_content_file,
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_error_handler(error_handler)

    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

