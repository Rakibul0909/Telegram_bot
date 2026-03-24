import logging
import datetime
import asyncio
import aiohttp
import json
import urllib.parse
import os
import re
import html
import secrets
import time
from pytz import timezone
from telegram import InputMediaPhoto
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# ========= ⚙️ CONFIGURATION ⚙️ =========
BOT_TOKEN = "8704843939:AAFxleFCm2PKbQHTq8lgEgkCBkoXE1QIWuE"

# ---- 🎯 API ENDPOINTS (REPLACE WITH YOUR ACTUAL URLs) ----
API_URL_LIKE = "https://likeapi.vercel.app/like?uid={uid}&server_name={region}"  # ✅ Fixed
API_URL_VISIT = "https://your.vercel.app/{region}/{uid}"          # ⚠️ REPLACE with real visit API
API_URL_SPAM_INFO = "https://your-0.vercel.app/{region}/{uid}?key=SPIDEYxVISIT"  # ⚠️ REPLACE with real spam info API
API_URL_SPAM_SEND = "http://127.0.0.1:5002/send_requests?uid={uid}&key=GOJOxZAXY" # ⚠️ REPLACE with real spam send API

API_GET_INFO = "https://gojoinfoapi-mu.vercel.app/get?uid={uid}&region={region}"
API_GET_OUTFIT = "https://ffoutfitapis.vercel.app/outfit-image?uid={uid}&region={region}&key=99day"

VERIFY_API_KEY = "1c78b01974f8fbaf6df0e924581b7908dec68830"
VERIFY_BASE_URL = "https://vplink.in/api"

OWNER_ID = 7558720792
ADMIN_IDS = [7558720792]
ALLOWED_GROUPS =[--1003601829158]

REQUIRED_CHANNELS =[
    {"username": "AjayFFCommunity", "url": "https://t.me/AjayFFCommunity", "name": "MAIN CHANNEL"},
    {"username": "AgAjayVipfiles", "url": "https://t.me/AgAjayVipfiles", "name": "FREE VIP FILES"},
    {"username": "AjayFFLikesgroup", "url": "https://t.me/AjayFFLikesgroup", "name": "AUTOLIKE GROUP"},
    {"username": "AjayFFLikeCommunity", "url": "https://t.me/AjayFFLikeCommunity", "name": "FREE LIKES"},
]

USER_LIMITS = { "like": 1, "visit": 6, "spam": 2, "get": 100 }

RESET_TIMEZONE = "Asia/Kolkata"
RESET_HOUR = 4
RESET_MINUTE = 30

# ========= 📝 FONT CONVERTER 📝 =========
def sc(text: str) -> str:
    """Safely converts string to Small Caps while protecting URLs, tags, and commands."""
    if not isinstance(text, str):
        return str(text)
    trans_map = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
    )
    pattern = r'(https?://\S+|tg://\S+|<[^>]+>|/\w+|@[a-zA-Z0-9_]+)'
    parts = re.split(pattern, text)
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].translate(trans_map)
    return "".join(parts)

# ========= 🗂️ STATE & DATA STORES 🗂️ =========
bot_enabled = True
user_data = {}
verification_enabled = True

VIP_USERS_FILE = "vip_users.json"
ALLOWED_GROUPS_FILE = "allowed_groups.json"
AUTOLIKE_TARGETS_FILE = "autolike_targets.json"
AUTOLIKE_LOG_FILE = "autolike_log.json"

pending_verifications = {}
MIN_WAIT_TIME = 180  # 3 minutes
MAX_WAIT_TIME = 600  # 10 minutes

# ========= 🪵 LOGGING 🪵 =========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========= 💾 DATA SAVING / LOADING 💾 =========
def load_vip_users() -> dict:
    if not os.path.exists(VIP_USERS_FILE):
        return {}
    try:
        with open(VIP_USERS_FILE, 'r') as f:
            data = json.load(f)
            return {int(k): datetime.datetime.fromisoformat(v) for k, v in data.items()}
    except Exception as e:
        logger.error(f"Error loading VIP users: {e}")
        return {}

def save_vip_users(vips: dict):
    try:
        with open(VIP_USERS_FILE, 'w') as f:
            data = {str(k): v.isoformat() for k, v in vips.items()}
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving VIP users: {e}")

def load_allowed_groups() -> set:
    groups = set(ALLOWED_GROUPS)
    if not os.path.exists(ALLOWED_GROUPS_FILE):
        return groups
    try:
        with open(ALLOWED_GROUPS_FILE, 'r') as f:
            data = json.load(f)
            groups.update(data)
    except Exception as e:
        logger.error(f"Error loading allowed groups: {e}")
    return groups

def save_allowed_groups(groups: set):
    try:
        with open(ALLOWED_GROUPS_FILE, 'w') as f:
            json.dump(list(groups), f, indent=2)
    except Exception as e:
        logger.error(f"Error saving allowed groups: {e}")

vip_users = load_vip_users()
allowed_groups = load_allowed_groups()

# ========= 헬 HELPER FUNCTIONS 헬 =========
def get_today_date():
    return datetime.datetime.now(timezone(RESET_TIMEZONE)).strftime("%Y-%m-%d")

def is_vip(user_id: int) -> bool:
    if user_id not in vip_users: return False
    if datetime.datetime.utcnow() > vip_users[user_id]:
        del vip_users[user_id]
        save_vip_users(vip_users)
        return False
    return True

def reset_user_if_needed(user_id: int):
    user_id_str = str(user_id)
    today = get_today_date()
    
    if user_id_str not in user_data:
        user_data[user_id_str] = {
            "reset_date": today,
            "verified_date": None,
            "counts": {"like": 0, "visit": 0, "spam": 0, "get": 0}
        }
        return

    if user_data[user_id_str].get("reset_date") != today:
        user_data[user_id_str]["counts"] = {"like": 0, "visit": 0, "spam": 0, "get": 0}
        user_data[user_id_str]["reset_date"] = today
        user_data[user_id_str]["verified_date"] = None

async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    try:
        user = await context.bot.get_chat(user_id)
        return user.full_name or f"User {user_id}"
    except Exception: return f"User {user_id}"

async def get_verification_link(payload: str, bot_username: str) -> str:
    destination_url = f"https://t.me/{bot_username}?start={payload}"
    encoded_destination_url = urllib.parse.quote(destination_url)
    api_url = f"{VERIFY_BASE_URL}?api={VERIFY_API_KEY}&url={encoded_destination_url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if isinstance(data, dict):
                        if data.get("status") == "success" and data.get("shortenedUrl"):
                            return data["shortenedUrl"]
                        elif data.get("shortenedUrl"):
                            return data["shortenedUrl"]
                        elif isinstance(data.get("url"), str):
                            return data["url"]
                        elif isinstance(data, str) and data.startswith("http"):
                            return data
                
                text_response = await resp.text()
                url_match = re.search(r'https?://[^\s"\'<>]+', text_response)
                if url_match:
                    return url_match.group(0)
                    
    except Exception as e:
        logger.error(f"Verification link error: {e}")
    
    return f"https://t.me/{bot_username}?start={payload}"

async def is_user_member_of_all_channels(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(f"@{channel['username']}", user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            logger.warning(f"Could not check membership for user {user_id} in channel @{channel['username']}")
            return False
    return True

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == OWNER_ID

async def enforce_channel_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if is_admin(user.id) or is_vip(user.id):
        return True
        
    if not await is_user_member_of_all_channels(context, user.id):
        keyboard = [[InlineKeyboardButton(sc(f"🔗 {c['name']}"), url=c['url'])] for c in REQUIRED_CHANNELS]
        keyboard.append([InlineKeyboardButton(sc("✅ I Have Joined"), callback_data=f"simplejoin_{user.id}")])
        
        await update.message.reply_text(
            sc("⚠️ **Action Required: Channel Verification**\n\nYou must join all our channels to use ANY command in this bot."),
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )
        return False
    return True

# ========= AUTO LIKE FUNCTIONS =========
def load_autolike_targets() -> list:
    if not os.path.exists(AUTOLIKE_TARGETS_FILE):
        return[]
    try:
        with open(AUTOLIKE_TARGETS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading autolike targets: {e}")
        return[]

def save_autolike_targets(targets: list):
    try:
        with open(AUTOLIKE_TARGETS_FILE, 'w') as f:
            json.dump(targets, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving autolike targets: {e}")

def load_autolike_log() -> dict:
    if not os.path.exists(AUTOLIKE_LOG_FILE):
        return {}
    try:
        with open(AUTOLIKE_LOG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading autolike log: {e}")
        return {}

def save_autolike_log(log_data: dict):
    try:
        with open(AUTOLIKE_LOG_FILE, 'w') as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving autolike log: {e}")

async def execute_autolike_cycle(app: Application):
    if not bot_enabled:
        return
        
    targets = load_autolike_targets()
    if not targets:
        return
    
    today = get_today_date()
    log_entries =[]
    
    for target in targets:
        region = target['region']
        uid = target['uid']
        
        try:
            url = API_URL_LIKE.format(uid=uid, region=region)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        api_data = data.get('response', {})
                        
                        log_entry = {
                            "Status": "Success",
                            "UID": uid,
                            "Region": region.upper(),
                            "PlayerNickname": api_data.get('PlayerNickname', 'N/A'),
                            "LikesGivenByAPI": api_data.get('LikesGivenByAPI', 0),
                            "RemainsLeft": api_data.get('RemainsLeft', 'N/A'),
                            "Timestamp": datetime.datetime.now().isoformat()
                        }
                        log_entries.append(log_entry)
                        
                        if api_data.get('LikesGivenByAPI', 0) > 0:
                            await app.bot.send_message(
                                OWNER_ID,
                                sc(f"✅ AutoLike Success!\n"
                                f"👤 Name: {api_data.get('PlayerNickname', 'N/A')}\n"
                                f"🆔 UID: {uid}\n"
                                f"🌍 Region: {region.upper()}\n"
                                f"🎉 Likes Given: {api_data.get('LikesGivenByAPI', 0)}\n"
                                f"💎 Remains: {api_data.get('RemainsLeft', 'N/A')}")
                            )
                    else:
                        log_entry = {
                            "Status": "Error",
                            "UID": uid,
                            "Region": region.upper(),
                            "Message": f"API Error: {resp.status}",
                            "Timestamp": datetime.datetime.now().isoformat()
                        }
                        log_entries.append(log_entry)
                        
        except Exception as e:
            log_entry = {
                "Status": "Error",
                "UID": uid,
                "Region": region.upper(),
                "Message": f"Exception: {str(e)}",
                "Timestamp": datetime.datetime.now().isoformat()
            }
            log_entries.append(log_entry)
            logger.error(f"Error in autolike for UID {uid}: {e}")
        
        await asyncio.sleep(2)
    
    log_data = {
        "date": today,
        "log": log_entries
    }
    save_autolike_log(log_data)
    
    success_count = sum(1 for entry in log_entries if entry.get("Status") == "Success")
    error_count = sum(1 for entry in log_entries if entry.get("Status") == "Error")
    
    await app.bot.send_message(
        OWNER_ID,
        sc(f"📊 AutoLike Cycle Complete!\n"
        f"✅ Success: {success_count}\n"
        f"❌ Errors: {error_count}\n"
        f"📅 Date: {today}")
    )

async def check_user_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE, command_type: str, args: list) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    user_id_str = str(user.id)
    bot_username = (await context.bot.get_me()).username

    if user.id in ADMIN_IDS or is_vip(user.id):
        return True

    reset_user_if_needed(user.id)
    
    current_count = user_data[user_id_str]["counts"].get(command_type, 0)
    max_limit = USER_LIMITS.get(command_type, 0)

    if current_count >= max_limit:
        limit_message = sc(
            "⛔ *𝗟𝗜𝗠𝗜𝗧 𝗥𝗘𝗔𝗖𝗛𝗘𝗗!*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Command:* `/{command_type}`\n"
            f"🔢 *Used:* `{current_count}/{max_limit}`\n"
            "⏰ *Reset Time:* 04:30 AM IST\n\n"
            "💎 *Want Unlimited?*\n"
            "👉 Contact @agajayofficial for VIP\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Try again tomorrow or upgrade to VIP!"
        )
        await update.message.reply_text(
            limit_message, 
            reply_to_message_id=update.message.message_id,
            parse_mode=ParseMode.MARKDOWN
        )
        return False

    if not await is_user_member_of_all_channels(context, user.id):
        payload = f"joinverify_{user.id}_{chat.id}_{command_type}_{'_'.join(args)}"
        keyboard = [[InlineKeyboardButton(sc(f"🔗 {c['name']}"), url=c['url'])] for c in REQUIRED_CHANNELS]
        keyboard.append([InlineKeyboardButton(sc("✅ I Have Joined & Verify"), callback_data=payload)])
        
        await update.message.reply_text(
            sc("⚠️ **Action Required: Channel Verification**\n\nPlease join our channels to use this bot."),
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode=ParseMode.MARKDOWN
        )
        return False

    today = get_today_date()
    
    if command_type == 'like' and verification_enabled and user_data[user_id_str].get("verified_date") != today:
        
        token = secrets.token_hex(8)
        pending_verifications[token] = {
            "user_id": user.id,
            "chat_id": chat.id,
            "command": command_type,
            "region": args[0],
            "uid": args[1],
            "timestamp": time.time()
        }
        
        payload = f"verify_{token}"
        verification_link = await get_verification_link(payload, bot_username)
        if not verification_link or not verification_link.startswith("http"):
            verification_link = f"https://t.me/{bot_username}?start={payload}"

        keyboard = [[InlineKeyboardButton(sc("✅ Verify & Run Command"), url=verification_link)],[InlineKeyboardButton(sc("❓ How to Verify"), url="https://t.me/ENDING_GAMER_77/241")]
        ]
        
        await update.message.reply_text(
            sc("╔══════════════════════════════╗\n"
            "║       🔐 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 𝗥𝗘𝗤𝗨𝗜𝗥𝗘𝗗     ║\n"
            "╚══════════════════════════════╝\n\n"
            f"👤 **Name** : {user.full_name}\n"
            f"🎯 **Command** : `/{command_type}`\n"
            f"🆔 **UID** : `{args[1]}`\n"
            f"🌍 **Region** : `{args[0].upper()}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Daily Used**: `{current_count}/{max_limit}`\n\n"
            "⚠️ *Please click the button below to verify and continue.*"),
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode=ParseMode.MARKDOWN
        )

        return False

    user_data[user_id_str]["counts"][command_type] = current_count + 1
    return True

# ========= AUTO LIKE COMMANDS =========
async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(sc("⛔ Admin only command."))
        return

    if len(context.args) != 2:
        await update.message.reply_text(sc("⚠️ Usage: /auto <region> <uid>"))
        return

    region, uid = context.args
    targets = load_autolike_targets()

    if any(t['uid'] == uid and t['region'] == region for t in targets):
        await update.message.reply_text(sc("⚠️ This UID is already in the autolike list."))
        return

    targets.append({"region": region, "uid": uid})
    save_autolike_targets(targets)
    await update.message.reply_text(sc(f"✅ Added UID `{uid}` ({region.upper()}) to autolike list."), parse_mode="Markdown")

async def removeauto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(sc("⛔ Admin only command."))
        return

    if len(context.args) != 2:
        await update.message.reply_text(sc("⚠️ Usage: /removeauto <region> <uid>"))
        return

    region, uid = context.args
    targets = load_autolike_targets()
    new_targets = [t for t in targets if not (t['uid'] == uid and t['region'] == region)]

    if len(new_targets) == len(targets):
        await update.message.reply_text(sc("⚠️ UID not found in autolike list."))
        return

    save_autolike_targets(new_targets)
    await update.message.reply_text(sc(f"✅ Removed UID `{uid}` ({region.upper()}) from autolike list."), parse_mode="Markdown")

async def autolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(sc("⛔ Admin only command."))
        return

    targets = load_autolike_targets()
    if not targets:
        await update.message.reply_text(sc("📭 No UIDs in autolike list."))
        return

    target_list = sc("🎯 <b>Auto Like Targets:</b>\n\n")
    for i, target in enumerate(targets, 1):
        target_list += sc(f"{i}. 🌍 <b>{target['region'].upper()}</b> | 🆔 <code>{target['uid']}</code>\n")

    await update.message.reply_text(target_list, parse_mode="HTML")

async def autolog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(sc("⛔ Admin only command."))
        return

    log_data = load_autolike_log()
    if not log_data:
        await update.message.reply_text(sc("📭 No autolike log found."))
        return

    date_str = log_data.get("date", "Unknown Date")
    log_entries = log_data.get("log",[])

    if not log_entries:
        await update.message.reply_text(sc(f"📅 {date_str}\n\n📭 No autolike activity recorded."))
        return

    formatted_log = sc(f"📅 {date_str}\n\n")
    for entry in log_entries:
        status = entry.get("Status", "Unknown")

        if status == "Success":
            formatted_log += sc(
                f"✅ Success\n"
                f"👤 Name: {entry.get('PlayerNickname', 'Unknown')}\n"
                f"🆔 UID: {entry.get('UID', 'N/A')}\n"
                f"🌍 Region: {entry.get('Region', 'N/A')}\n"
                f"🎉 Likes Given: {entry.get('LikesGivenByAPI', 'N/A')}\n"
                f"💎 Remains: {entry.get('RemainsLeft', 'N/A')}\n"
                f"{'-'*25}\n"
            )
        elif status == "Error":
            formatted_log += sc(
                f"❌ Error\n"
                f"🆔 UID: {entry.get('UID', 'N/A')}\n"
                f"🌍 Region: {entry.get('Region', 'N/A')}\n"
                f"⚠️ Message: {entry.get('Message', 'Unknown error')}\n"
                f"{'-'*25}\n"
            )
        else:
            formatted_log += sc(f"ℹ️ Unknown entry: {entry}\n{'-'*25}\n")

    await update.message.reply_text(formatted_log)

# ========= 🔧 FIXED EXECUTION LOGIC =========
async def _execute_like_command(context: ContextTypes.DEFAULT_TYPE, chat_id: int, region: str, uid: str, user_username: str, reply_to_message_id: int = None):
    progress_msg = None
    try:
        progress_msg = await context.bot.send_message(chat_id=chat_id, text=sc("⏳ Starting... 0%"), reply_to_message_id=reply_to_message_id)

        progress_steps =[
            ("🚀 Connecting to server...", 25),
            ("📡 Validating UID...", 50),
            ("🧠 Sending Likes...", 75),
            ("✅ Finalizing...", 100)
        ]

        for text, percent in progress_steps:
            await asyncio.sleep(0.4)
            await progress_msg.edit_text(sc(f"{text} {percent}%"))

        url = API_URL_LIKE.format(uid=uid, region=region)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    await progress_msg.edit_text(sc(f"🚨 API Error! Status code: {resp.status}"))
                    return
                full_data = await resp.json()

        # 🛠️ FIX: Handle response keys with spaces
        api_data = full_data.get('response', full_data)  # sometimes 'response' is not present
        likes_given = api_data.get('LikesGiven ByAPI', api_data.get('LikesGivenByAPI', 0))
        nickname = api_data.get('PlayerNickname', 'N/A')
        before = api_data.get('LikesbeforeCommand', api_data.get('LikesbeforeCommand', 'N/A'))
        after = api_data.get('Likesafter Command', api_data.get('LikesafterCommand', 'N/A'))

        # If likes_given is still 0, maybe the API returned a message
        if likes_given == 0 and 'message' in api_data:
            await progress_msg.edit_text(sc(f"⚠️ {api_data['message']}"))
            return

        keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(sc("MAIN CHANNEL"), url="https://t.me/AjayFFCommunity"),
                InlineKeyboardButton(sc("OWNER"), url="https://t.me/agajayofficial")
            ]
        ])

        if likes_given == 0:
            api_text = sc(
                f"⚠️ 𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐰𝐢𝐭𝐡 𝐔𝐈𝐃 [{uid}] 𝐡𝐚𝐬 𝐫𝐞𝐚𝐜𝐡𝐞𝐝 𝐭𝐡𝐞 𝐦𝐚𝐱𝐢𝐦𝐮𝐦 𝐥𝐢𝐤𝐞𝐬 𝐟𝐨𝐫 𝐭𝐨𝐝𝐚𝐲.\n"
                "⏳ Please try again tomorrow."
            )
        else:
            api_text = sc(
                "🚀 𝐔𝐈𝐃 𝐕𝐚𝐥𝐢𝐝𝐚𝐭𝐞𝐝 - 𝐀𝐏𝐈 𝐜𝐨𝐧𝐧𝐞𝐜𝐭𝐞𝐝\n\n"
                f"🆔 | 𝐔𝐈𝐃: `{uid}`\n"
                f"👤 | 𝐍𝐚𝐦𝐞: `{nickname}`\n"
                f"🌍 | 𝐑𝐞𝐠𝐢𝐨𝐧: `{region.upper()}`\n"
                "📝 𝐋𝐢𝐤𝐞𝐬 𝐝𝐞𝐭𝐚𝐢𝐥𝐬\n\n"
                f"🐥 | 𝐋𝐢𝐤𝐞𝐬 𝐁𝐞𝐟𝐨𝐫𝐞: `{before}`\n"
                f"🐲 | 𝐋𝐢𝐤𝐞𝐬 𝐀𝐟𝐭𝐞𝐫: `{after}`\n"
                f"🐉 | 𝐋𝐢𝐤𝐞𝐬 𝐆𝐢𝐯𝐞𝐧: `+{likes_given}`\n\n"
                f"👤 | 𝐒𝐞𝐧𝐭 𝐁𝐲: @{user_username}"
                "\n[‌](https://iili.io/33PVMKl.md.jpg)"
            )

        await context.bot.send_message(
            chat_id=chat_id,
            text=api_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply_to_message_id
        )

        if progress_msg:
            await progress_msg.delete()

    except asyncio.TimeoutError:
        if progress_msg: await progress_msg.edit_text(sc("⏱️ API request timed out."))
    except Exception as e:
        if progress_msg: await progress_msg.delete()
        await context.bot.send_message(chat_id=chat_id, text=sc(f"❌ Unexpected error: {str(e)}"), reply_to_message_id=reply_to_message_id)

async def _execute_visit_command(context: ContextTypes.DEFAULT_TYPE, chat_id: int, region: str, uid: str, user_mention: str = "", reply_to_message_id: int = None):
    # ⚠️ WARNING: This uses a placeholder API URL. Replace with your actual visit API.
    if API_URL_VISIT == "https://your.vercel.app/{region}/{uid}":
        await context.bot.send_message(chat_id, sc("❌ Visit API not configured. Please set API_URL_VISIT in the code."), reply_to_message_id=reply_to_message_id)
        return

    user_username = user_mention if user_mention else "User"
    safe_username = html.escape(user_username)
    
    processing_msg = await context.bot.send_message(
        chat_id, 
        sc(f"⏳ <b>Processing your visit request...</b>"), 
        parse_mode=ParseMode.HTML,
        reply_to_message_id=reply_to_message_id
    )
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL_VISIT.format(region=region, uid=uid), timeout=30) as resp:
                if resp.status != 200: 
                    await processing_msg.edit_text(
                        sc(f"❌ API Error: <b>{resp.status}</b>"), 
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    text_response = await resp.text()
                    logger.error(f"Unexpected response format: {content_type} - {text_response[:200]}")
                    await processing_msg.edit_text(
                        sc("⚠️ Unexpected API response format. Please try again later."),
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                data = await resp.json()
        
        nickname = str(data.get('nickname', 'N/A'))
        safe_nickname = html.escape(nickname)
        
        uid_response = str(data.get('uid', uid))
        safe_uid = html.escape(uid_response)
        
        region_display = str(data.get('region', region.upper()))
        safe_region = html.escape(region_display)
        
        level = str(data.get('level', 'N/A'))
        safe_level = html.escape(level)
        
        likes = str(data.get('likes', 'N/A'))
        safe_likes = html.escape(likes)
        
        success = data.get('success', 0)
        fail = data.get('fail', 0)
        
        reply_text = sc(
            "╭─────────────────────⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡─────────────────────╮\n"
            "┃                    🌌 𝗚𝗔𝗠𝗘𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘 𝗥𝗘𝗣𝗢𝗥𝗧                   ┃\n"
            "╰─────────────────────⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡⟡─────────────────────╯\n"
            f"🎮 <b>Name</b>       : <code>{safe_nickname}</code>\n"
            f"🆔 <b>UID</b>        : <code>{safe_uid}</code>\n"
            f"🌍 <b>Region</b>     : <b>{safe_region}</b>\n"
            f"📶 <b>Level</b>      : <b>{safe_level}</b>\n"
            f"💖 <b>Likes</b>      : <b>{safe_likes}</b>\n"
            f"📩 <b>Visit Status</b> : ✅ <b>{success}</b>    ❌ <b>{fail}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 <i>Generated securely by</i> <b>@agajayofficial</b>\n"
            f"👤 <i>Requested by</i> <b>@{safe_username}</b>"
        )
        
        await processing_msg.edit_text(reply_text, parse_mode=ParseMode.HTML)
        
    except asyncio.TimeoutError:
        await processing_msg.edit_text(
            sc("⏱️ API request timed out. Please try again later."), 
            parse_mode=ParseMode.HTML
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in visit command: {e}")
        await processing_msg.edit_text(
            sc("⚠️ Invalid JSON response from API. Please try again later."),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Visit execution error: {e}")
        await processing_msg.edit_text(
            sc(f"⚠️ Unexpected error: <code>{html.escape(str(e))}</code>"), 
            parse_mode=ParseMode.HTML
        )

async def _execute_spam_command(context: ContextTypes.DEFAULT_TYPE, chat_id: int, region: str, uid: str, user_mention: str = "", reply_to_message_id: int = None):
    # ⚠️ WARNING: Spam APIs are placeholders. Replace with your actual endpoints.
    if API_URL_SPAM_SEND == "http://127.0.0.1:5002/send_requests?uid={uid}&key=GOJOxZAXY" or API_URL_SPAM_INFO == "https://your-0.vercel.app/{region}/{uid}?key=SPIDEYxVISIT":
        await context.bot.send_message(chat_id, sc("❌ Spam API not configured. Please set API_URL_SPAM_SEND and API_URL_SPAM_INFO in the code."), reply_to_message_id=reply_to_message_id)
        return

    user_username = user_mention if user_mention else "User"
    processing_msg = await context.bot.send_message(chat_id, sc(f"⏳ {user_mention} Running `/spam` command..."), reply_to_message_id=reply_to_message_id)
    nickname = "N/A"
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(API_URL_SPAM_INFO.format(region=region, uid=uid), timeout=10) as resp:
                    if resp.status == 200: 
                        nickname = (await resp.json()).get("nickname", "N/A")
            except Exception: 
                pass
            async with session.get(API_URL_SPAM_SEND.format(uid=uid), timeout=60) as resp:
                if resp.status != 200: 
                    await processing_msg.edit_text(sc(f"❌ Error: Spam service returned status {resp.status}."))
                    return
                data = await resp.json()
        success = data.get('success_count', 0)
        failed = data.get('failed_count', 0)
        text = sc(
            f"✨ **Spam Request Result:**\n\n"
            f"🆔 UID: `{uid}`\n"
            f"👤 Name: `{nickname}`\n"
            f"✅ Success: `{success}`\n"
            f"❌ Failed: `{failed}`\n"
            f"🌡️ Total: `{success + failed}`\n\n"
            f"🔰 Credit: @agajayofficial\n"
            f"👤 Sent By: @{user_username}"
        )
        await processing_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Spam execution error: {e}")
        await processing_msg.edit_text(sc("❌ An unexpected error occurred."))

# ========= CALLBACK HANDLER =========
async def handle_join_verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        data = query.data.split('_')
        
        if data[0] == "simplejoin":
            return

        if data[0] == "joinverify" and len(data) >= 6:
            payload_user_id, source_group_id, command_to_run, region, uid = int(data[1]), int(data[2]), data[3], data[4], data[5]

            if query.from_user.id != payload_user_id:
                await query.edit_message_text(sc("❌ This verification button is not for you."))
                return

            if not await is_user_member_of_all_channels(context, query.from_user.id):
                keyboard =[
                    [InlineKeyboardButton(sc(f"🔗 {c['name']}"), url=c['url'])] for c in REQUIRED_CHANNELS
                ]
                keyboard.append([InlineKeyboardButton(sc("❌ Not Joined All - Re-Verify"), callback_data=query.data)]
                )
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    sc("❌ **Error: Channel Verification Failed!**\n\n"
                    "You have NOT joined all the channels. Please join them all, then click the button again."),
                    reply_markup=reply_markup, 
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            today = get_today_date()
            user_id_str = str(query.from_user.id)
            bot_username = (await context.bot.get_me()).username
            
            if command_to_run == 'like' and verification_enabled and user_data.get(user_id_str, {}).get("verified_date") != today:
                payload = f"verify_{payload_user_id}_{source_group_id}_{command_to_run}_{region}_{uid}"
                verification_link = await get_verification_link(payload, bot_username)
                
                keyboard = [[InlineKeyboardButton(sc("✅ Complete Daily Verification"), url=verification_link)],[InlineKeyboardButton(sc("❓ How to Verify"), url="https://t.me/ENDING_GAMER_77/241")]
                ]
                
                await query.edit_message_text(
                    sc("✅ **Channel Verification Passed!**\n\n"
                    "Now complete your daily verification to run the /like command:"),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                user_username = query.from_user.username if query.from_user.username else query.from_user.first_name
                
                if not (query.from_user.id in ADMIN_IDS or is_vip(query.from_user.id)):
                    reset_user_if_needed(query.from_user.id)
                    current_count = user_data[user_id_str]["counts"].get(command_to_run, 0)
                    max_limit = USER_LIMITS.get(command_to_run, 0)
                    
                    if current_count >= max_limit:
                        await query.edit_message_text(
                            sc("⛔ You've reached your daily limit for this command."),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        return
                    
                    user_data[user_id_str]["counts"][command_to_run] = current_count + 1
                
                if command_to_run == 'like':
                    await _execute_like_command(context, source_group_id, region, uid, user_username, None)
                elif command_to_run == 'visit':
                    await _execute_visit_command(context, source_group_id, region, uid, user_username, None)
                elif command_to_run == 'spam':
                    await _execute_spam_command(context, source_group_id, region, uid, user_username, None)
                elif command_to_run == 'get':
                    await _execute_get_command(context, source_group_id, region, uid, user_username, None)
                
                await query.edit_message_text(
                    sc(f"✅ Channel verification complete! Your `/{command_to_run}` command has been executed."),
                    parse_mode=ParseMode.MARKDOWN
                )

    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            await query.edit_message_text(sc("❌ An error occurred. Please try sending the command again."))
        except:
            pass

# ========= 🤖 CORE COMMANDS 🤖 =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await enforce_channel_join(update, context):
        return

    user = update.effective_user
    user_id_str = str(user.id)
    today = get_today_date()
    
    reset_user_if_needed(user.id)

    if context.args and context.args[0].startswith("verify_"):
        try:
            token = context.args[0].replace("verify_", "")
            
            if token not in pending_verifications:
                await update.message.reply_text(
                    sc("❌ **Invalid or Expired Link!**\nYeh link expire ho chuka hai, use ho chuka hai ya galat hai. Please command wapas bhej kar naya link generate karein."),
                    reply_to_message_id=update.message.message_id
                )
                return

            v_data = pending_verifications[token]
            time_passed = time.time() - v_data["timestamp"]

            if time_passed > MAX_WAIT_TIME:
                del pending_verifications[token]
                await update.message.reply_text(
                    sc("⏰ **Link Expired!**\n\nAapne 10 minute se zyada time laga diya. Token expire ho chuka hai. Kripya wapas jaake naya link banayein."),
                    reply_to_message_id=update.message.message_id
                )
                return
            
            if time_passed < MIN_WAIT_TIME:
                del pending_verifications[token]
                await update.message.reply_text(
                    sc("⚠️ ᴍᴀᴅᴀʀᴄʜᴏᴅ ʙʏᴘᴀꜱꜱ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ!\n"
                       "ʀᴀɴᴅɪ ᴋᴇ ʙᴀᴄʜᴇ ᴠᴇʀɪꜰʏ ᴋᴀʀɴᴇ ᴍᴇ ᴍᴀᴀ ᴄʜᴜᴅ ʀʜᴀ ʜᴀɪ ᴋʏᴀ ᴊᴏ ʙʏᴘᴀꜱꜱ ᴋɪʏᴀ\n"
                       "❌ ʙʏᴘᴀꜱꜱ ᴅᴇᴛᴇᴄᴛᴇᴅ - ɴᴏ like"),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=update.message.message_id
                )
                return

            payload_user_id = v_data["user_id"]
            source_group_id = v_data["chat_id"]
            command_to_run = v_data["command"]
            region = v_data["region"]
            uid = v_data["uid"]
            
            if user.id != payload_user_id: 
                await update.message.reply_text(
                    sc("❌ Verification failed. Yeh link kisi aur user ke liye generate hua tha."),
                    reply_to_message_id=update.message.message_id
                )
                return

            del pending_verifications[token]

            if not (user.id in ADMIN_IDS or is_vip(user.id)):
                current_count = user_data[user_id_str]["counts"].get(command_to_run, 0)
                max_limit = USER_LIMITS.get(command_to_run, 0)
                
                if current_count >= max_limit:
                    limit_message = sc(
                        "⛔ *𝗟𝗜𝗠𝗜𝗧 𝗥𝗘𝗔𝗖𝗛𝗘𝗗!*\n\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        f"📊 *Command:* `/{command_to_run}`\n"
                        f"🔢 *Used:* `{current_count}/{max_limit}`\n"
                        "⏰ *Reset Time:* 04:30 AM IST\n\n"
                        "💎 *Want Unlimited?*\n"
                        "👉 Contact @agajayofficial for VIP\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        "⚠️ Try again tomorrow or upgrade to VIP!"
                    )
                    
                    await update.message.reply_text(
                        limit_message,
                        reply_to_message_id=update.message.message_id,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            if command_to_run == 'like':
                if user_data[user_id_str].get("verified_date") != today:
                    user_data[user_id_str]["verified_date"] = today
                    await update.message.reply_text(
                        sc("✅ **Verification Successful!**\n\n"
                        f"Your command `/{command_to_run}` is being executed in the group."),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_to_message_id=update.message.message_id
                    )
                else:
                    await update.message.reply_text(
                        sc("✅ You were already verified today. Executing your command..."),
                        reply_to_message_id=update.message.message_id
                    )
            else:
                await update.message.reply_text(
                    sc(f"✅ Processing your `/{command_to_run}` command..."),
                    reply_to_message_id=update.message.message_id
                )
            
            if not (user.id in ADMIN_IDS or is_vip(user.id)):
                user_data[user_id_str]["counts"][command_to_run] = current_count + 1
            
            user_username = user.username if user.username else user.first_name
            
            if command_to_run == 'like': 
                await _execute_like_command(context, source_group_id, region, uid, user_username, None)
            elif command_to_run == 'visit': 
                await _execute_visit_command(context, source_group_id, region, uid, user_username, None)
            elif command_to_run == 'spam': 
                await _execute_spam_command(context, source_group_id, region, uid, user_username, None)
            elif command_to_run == 'get':
                await _execute_get_command(context, source_group_id, region, uid, user_username, None)
            
            await context.bot.send_message(
                chat_id=source_group_id,
                text=sc(f"✅ {user.mention_html()} has completed verification and executed `/{command_to_run}`"),
                parse_mode=ParseMode.HTML
            )
            return
            
        except Exception as e: 
            logger.error(f"Error in token verification: {e}")
            await update.message.reply_text(
                sc("❌ Kuch error aayi hai. Kripya dobara try karein."),
                reply_to_message_id=update.message.message_id
            )
            return
        except (ValueError, IndexError) as e: 
            logger.warning(f"Malformed payload: {context.args[0]} - Error: {e}")
    
    elif context.args and context.args[0].startswith("joinverify_"):
        try:
            parts = context.args[0].split('_')
            if len(parts) >= 6:
                payload_user_id, source_group_id, command_to_run, region, uid = int(parts[1]), int(parts[2]), parts[3], parts[4], parts[5]
                
                if user.id != payload_user_id:
                    await update.message.reply_text(sc("❌ This verification link is not for you."))
                    return
                
                if not await is_user_member_of_all_channels(context, user.id):
                    keyboard = [[InlineKeyboardButton(sc(f"🔗 {c['name']}"), url=c['url'])] for c in REQUIRED_CHANNELS]
                    await update.message.reply_text(
                        sc("❌ You haven't joined all channels yet. Please join them and click the button again."),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
                
                if verification_enabled and user_data[user_id_str].get("verified_date") != today:
                    payload = f"verify_{user.id}_{source_group_id}_{command_to_run}_{region}_{uid}"
                    verification_link = await get_verification_link(payload, (await context.bot.get_me()).username)
                    
                    keyboard =[
                        [InlineKeyboardButton(sc("✅ Complete Daily Verification"), url=verification_link)],[InlineKeyboardButton(sc("❓ How to Verify"), url="https://t.me/ENDING_GAMER_77/241")]
                    ]
                    
                    await update.message.reply_text(
                        sc("✅ **Channel Verification Passed!**\n\n"
                        "Now complete your daily verification to run the command:"),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    user_username = user.username if user.username else user.first_name
                    
                    if command_to_run == 'like': 
                        await _execute_like_command(context, source_group_id, region, uid, user_username, None)
                    elif command_to_run == 'visit': 
                        await _execute_visit_command(context, source_group_id, region, uid, user_username, None)
                    elif command_to_run == 'spam': 
                        await _execute_spam_command(context, source_group_id, region, uid, user_username, None)
                    elif command_to_run == 'get':
                        await _execute_get_command(context, source_group_id, region, uid, user_username, None)
                    
                    await update.message.reply_text(sc(f"✅ Channel verification passed! Your `/{command_to_run}` command has been executed."))
                return
        except (ValueError, IndexError) as e:
            logger.warning(f"Malformed joinverify payload: {context.args[0]} - Error: {e}")
    
    welcome_text = sc(
        "👋 **Welcome to Free Fire Premium Bot!**\n\n"
        "🌟 **Features:**\n"
        "• Free Likes for your account\n"
        "• Profile Visits\n"
        "• Friend Requests (Spam)\n"
        "• Detailed Player Info\n\n"
        "📌 **How to Use:**\n"
        "1. Join all required channels\n"
        "2. Use /like, /visit, /spam, or /get commands\n"
        "3. Complete daily verification\n"
        "4. Enjoy the service!\n\n"
        "📊 Check your limits with /check\n"
        "❓ Need help? Use /help"
    )
    
    keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(sc("📢 Updates"), url="https://t.me/AjayFFCommunity"),
            InlineKeyboardButton(sc("👨‍💻 Developer"), url="https://t.me/agajayofficial")
        ]
    ])
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        reply_to_message_id=update.message.message_id
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await enforce_channel_join(update, context):
        return

    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    help_text = sc(
        "📘 <b>HELP MENU - ALL COMMANDS</b>\n\n"
        
        "👤 <b>USER COMMANDS:</b>\n"
        "/like {region} {uid} - Send free likes\n"
        "/visit {region} {uid} - Visit player profile\n"
        "/spam {region} {uid} - Send friend requests\n"
        "/get {region} {uid} - Get player info\n"
        "/check - Check your daily limits\n"
        "/start - Start the bot\n"
        "/help - Show this help menu\n\n"
        
        "🔧 <b>BOT MANAGEMENT (Admin Only):</b>\n"
        "/on - Turn bot ON\n"
        "/off - Turn bot OFF\n"
        "/allow {group_id} - Allow a group\n"
        "/remove {group_id} - Remove a group\n"
        "/broadcast {message} - Broadcast message\n"
        "/stats - Show bot statistics\n\n"
        
        "👑 <b>VIP MANAGEMENT (Admin Only):</b>\n"
        "/setvip {user_id} {days} - Add VIP\n"
        "/removevip {user_id} - Remove VIP\n"
        "/viplist - List VIP users\n\n"
        
        "🔐 <b>VERIFICATION SYSTEM (Admin Only):</b>\n"
        "/startverify - Enable verification\n"
        "/stopverify - Disable verification\n"
        "/verifystatus - Check verification status\n\n"
        
        "🔄 <b>AUTO LIKE SYSTEM (Admin Only):</b>\n"
        "/auto {region} {uid} - Add to autolike\n"
        "/removeauto {region} {uid} - Remove from autolike\n"
        "/autolist - Show autolike targets\n"
        "/autolog - Show autolike logs\n\n"
        
        "👥 <b>USER MANAGEMENT (Admin Only):</b>\n"
        "/userinfo {user_id} - Get user info\n"
        "/addadmin {user_id} - Add admin (Owner only)\n"
        "/removeadmin {user_id} - Remove admin (Owner only)\n\n"
        
        "📝 <b>USAGE NOTES:</b>\n"
        "• {region}: ind, br, bd, pk, etc.\n"
        "• {uid}: Player's UID number\n"
        "• Daily limits reset at 04:30 AM IST\n"
        "• VIP users have unlimited access\n"
        "• Join required channels before using\n\n"
        
        "🔗 <b>CHANNELS:</b>\n"
        "@AjayFFCommunity - Updates\n"
        "@AgAjayVipfiles - Free APIs\n"
        "@AjayFFLikeCommunity - Group\n\n"
        
        "👨‍💻 <b>DEVELOPER:</b> @agajayofficial"
    )
    
    keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(sc("📢 UPDATES"), url="https://t.me/AjayFFLikeCommunity"),
            InlineKeyboardButton(sc("👨‍💻 DEVELOPER"), url="https://t.me/agajayofficial")
        ]
    ])
    
    await update.message.reply_text(
        help_text, 
        parse_mode=ParseMode.HTML, 
        reply_markup=keyboard,
        reply_to_message_id=update.message.message_id
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await enforce_channel_join(update, context):
        return

    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    user = update.effective_user
    if is_vip(user.id): 
        await update.message.reply_text(sc("🌟 You are a VIP! You have unlimited access."), reply_to_message_id=update.message.message_id)
        return
    
    reset_user_if_needed(user.id)
    counts = user_data[str(user.id)]['counts']
    verified = sc("✅ Yes") if user_data[str(user.id)].get("verified_date") == get_today_date() else sc("❌ No")
    
    status_text = sc(
        f"👤 **Your Daily Status**\n\n"
        f"Verified Today: **{verified}**\n\n"
        f"👍 Likes: `{counts.get('like', 0)}/{USER_LIMITS['like']}`\n"
        f"👀 Visits: `{counts.get('visit', 0)}/{USER_LIMITS['visit']}`\n"
        f"🔥 Spam: `{counts.get('spam', 0)}/{USER_LIMITS['spam']}`\n"
        f"📊 Get Info: `{counts.get('get', 0)}/{USER_LIMITS['get']}`"
    )
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    if update.effective_chat.id not in allowed_groups: 
        return
    
    if len(context.args) != 2: 
        await update.message.reply_text(sc("⚠️ Usage: `/like <region> <uid>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        return
    
    if await check_user_permissions(update, context, "like", context.args):
        user = update.effective_user
        user_username = user.username if user.username else user.first_name
        await _execute_like_command(context, update.effective_chat.id, context.args[0], context.args[1], user_username, update.message.message_id)

async def visit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    if update.effective_chat.id not in allowed_groups: 
        return
    
    if len(context.args) != 2: 
        await update.message.reply_text(sc("⚠️ Usage: `/visit <region> <uid>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        return
    
    if await check_user_permissions(update, context, "visit", context.args):
        user = update.effective_user
        user_username = user.username if user.username else user.first_name
        await _execute_visit_command(context, update.effective_chat.id, context.args[0], context.args[1], user_username, update.message.message_id)

async def spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    if update.effective_chat.id not in allowed_groups: 
        return
    
    if len(context.args) != 2: 
        await update.message.reply_text(sc("⚠️ Usage: `/spam <region> <uid>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        return
    
    if await check_user_permissions(update, context, "spam", context.args):
        user = update.effective_user
        user_username = user.username if user.username else user.first_name
        await _execute_spam_command(context, update.effective_chat.id, context.args[0], context.args[1], user_username, update.message.message_id)

# ========= 📄 GET COMMAND (UNCHANGED) =========
def ts(stamp):
    try:
        return datetime.datetime.utcfromtimestamp(int(stamp)).strftime('%d %b %Y at %H:%M:%S')
    except:
        return "—"

def cs_rank_from_stars(stars):
    try:
        stars = int(stars)
    except:
        return "Unknown"

    if stars >= 187: return "Elite Master"
    elif stars >= 137: return "Master"
    elif stars >= 112: return "Elite Heroic"
    elif stars >= 87: return "Heroic"
    elif stars >= 82: return "Diamond V"
    elif stars >= 77: return "Diamond IV"
    elif stars >= 72: return "Diamond III"
    elif stars >= 67: return "Diamond II"
    elif stars >= 62: return "Diamond I"
    elif stars >= 57: return "Platinum V"
    elif stars >= 52: return "Platinum IV"
    elif stars >= 47: return "Platinum III"
    elif stars >= 42: return "Platinum II"
    elif stars >= 37: return "Platinum I"
    elif stars >= 33: return "Gold IV"
    elif stars >= 29: return "Gold III"
    elif stars >= 25: return "Gold II"
    elif stars >= 21: return "Gold I"
    elif stars >= 17: return "Silver III"
    elif stars >= 13: return "Silver II"
    elif stars >= 9: return "Silver I"
    elif stars >= 6: return "Bronze III"
    elif stars >= 3: return "Bronze II"
    elif stars >= 0: return "Bronze I"
    else: return "Unknown"

def br_rank_from_points(points):
    try:
        points = int(points)
    except:
        return "Unknown"

    if points >= 10000: return "Elite Master V"
    elif points >= 9000: return "Elite Master IV"
    elif points >= 8000: return "Elite Master III"
    elif points >= 7100: return "Master II"
    elif points >= 6300: return "Master I"
    elif points >= 5500: return "Elite Heroic V"
    elif points >= 4900: return "Elite Heroic IV"
    elif points >= 4300: return "Elite Heroic III"
    elif points >= 3800: return "Heroic II"
    elif points >= 3500: return "Heroic I"
    elif points >= 2750: return "Diamond"
    elif points >= 2000: return "Platinum"
    elif points >= 1600: return "Gold"
    elif points >= 1300: return "Silver"
    elif points >= 1000: return "Bronze"
    else: return "Unranked"

def format_info(uid, data):
    account = data.get("AccountInfo", {})
    profile = data.get("AccountProfileInfo", {})
    guild = data.get("GuildInfo", {})
    captain = data.get("captainBasicInfo", {})
    credit = data.get("creditScoreInfo", {})
    pet = data.get("petInfo", {})
    social = data.get("socialinfo", {})
    
    outfit_ids = profile.get("EquippedOutfit",[])
    outfit_text = ", ".join(str(x) for x in outfit_ids[:3]) + ("..." if len(outfit_ids) > 3 else "") if outfit_ids else "None"
    
    skills = profile.get("EquippedSkills",[])
    skill_text = f"{len(skills)//4} sets equipped" if skills else "None"
    
    return sc(f"""
<b>👤 PLAYER PROFILE DETAILS</b>
<pre>
🎮 Account Overview ───────────────────────
🔹 Nickname      : {account.get("AccountName")}
🆔 UID           : {uid}
🌍 Region        : {account.get("AccountRegion")}
📈 Level         : {account.get("AccountLevel")} (Exp: {account.get("AccountEXP")})
❤️ Likes         : {account.get("AccountLikes")}
🏷️ Title ID      : {account.get("Title")}
✍️ Signature     : {social.get("signature") or 'None'}

🕒 Activity Info ──────────────────────────
📅 Created On     : {ts(account.get("AccountCreateTime"))}
♻️ Last Login     : {ts(account.get("AccountLastLogin"))}
🧾 OB Version     : {account.get("ReleaseVersion") or '—'}

🏅 Rank Information ───────────────────────
🏹 BR Rank        : {br_rank_from_points(account.get("BrRankPoint"))} ({account.get("BrRankPoint")})
🔫 CS Rank        : {cs_rank_from_stars(account.get("CsRankPoint"))} ({account.get("CsRankPoint")})
🎯 BR Max Rank    : {account.get("BrMaxRank")}
🎯 CS Max Rank    : {account.get("CsMaxRank")}
🔁 Season         : {account.get("AccountSeasonId")}
🎖️ BP Badges      : {account.get("AccountBPBadges")}x
🔥 BP ID          : {account.get("AccountBPID")}

🎨 Avatar & Style ────────────────────────
🖼️ Avatar ID      : {account.get("AccountAvatarId")}
🪧 Banner ID      : {account.get("AccountBannerId") or 'Not Set'}
🔫 Gun Skin       : {account.get("EquippedWeapon", ['—'])[0] if account.get("EquippedWeapon") else '—'}
👕 Outfits        : {outfit_text}
⚡ Skills         : {skill_text}

💎 Credit Info ───────────────────────────
💠 Credit Score   : {credit.get("creditScore")}
⏱️ Period End     : {ts(credit.get("periodicSummaryEndTime"))}
🎁 Reward State   : {credit.get("rewardState")}

🐾 Pet Info ──────────────────────────────
🐶 Equipped       : {"✅ Yes" if pet.get("isSelected") else "❌ No"}
🆔 Pet ID         : {pet.get("id")}
📊 Pet Exp        : {pet.get("exp")}
📈 Pet Level      : {pet.get("level")}
🎯 Pet Skill      : {pet.get("selectedSkillId")}

🏰 Guild Info ─────────────────────────────
🏷️ Guild Name     : {guild.get("GuildName") or 'None'}
🆔 Guild ID       : {guild.get("GuildID") or '—'}
📶 Guild Level    : {guild.get("GuildLevel") or '—'}
👥 Members        : {guild.get("GuildMember") or 0}/{guild.get("GuildCapacity") or '—'}

👑 Guild Leader ──────────────────────────
👤 Leader Name    : {captain.get("nickname")}
🆔 Leader UID     : {captain.get("accountId")}
📈 Leader Level   : {captain.get("level")} (Exp: {captain.get("exp")})
❤️ Leader Likes   : {captain.get("liked")}
📅 Created At     : {ts(captain.get("createAt"))}
♻️ Last Login     : {ts(captain.get("lastLoginAt"))}
🎖️ Leader Badges  : {captain.get("badgeCnt")}
🏹 Leader BR      : {br_rank_from_points(captain.get("rankingPoints"))} ({captain.get("rankingPoints")})
🔫 Leader CS      : {cs_rank_from_stars(captain.get("csRankingPoints"))} ({captain.get("csRankingPoints")})
</pre>
🧥 <b>Outfit Preview Shown Below 👇</b>
""")

async def _execute_get_command(context, chat_id: int, region: str, uid: str, user_username: str, reply_to_message_id: int = None):
    try:
        progress_msg = await context.bot.send_message(chat_id=chat_id, text=sc("⏳ Fetching player info..."), reply_to_message_id=reply_to_message_id)

        info_url = API_GET_INFO.format(uid=uid, region=region)
        data = None
        
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
        
        if not data:
            await progress_msg.edit_text(sc("❌ Failed to fetch info. API might be down or UID is invalid."))
            return

        try:
            api_text = format_info(uid, data)
        except Exception as e:
            await progress_msg.edit_text(sc(f"❌ Error formatting data: {str(e)}"))
            return

        outfit_url = API_GET_OUTFIT.format(uid=uid, region=region)
        
        keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(sc("📢 Updates"), url="https://t.me/AjayFFCommunity"),
                InlineKeyboardButton(sc("👨‍💻 Coder"), url="https://t.me/agajayofficial")
            ]
        ])

        await progress_msg.edit_text(
            text=api_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=outfit_url,
                caption=sc("🧥 <b>Outfit Preview</b>"),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=progress_msg.message_id
            )
        except Exception as img_err:
            logger.error(f"Failed to send outfit image: {img_err}")

    except asyncio.TimeoutError:
        try: await progress_msg.edit_text(sc("⏱️ API request timed out."))
        except: pass
    except Exception as e:
        try: await context.bot.send_message(chat_id, sc(f"❌ Unexpected error: {str(e)}"), reply_to_message_id=reply_to_message_id)
        except: pass

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not bot_enabled:
        await update.message.reply_text(sc("🚫 Bot is currently turned off."), reply_to_message_id=update.message.message_id)
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(sc("❌ Usage: /get <region> <uid>\nExample: /get ind 123456789"), reply_to_message_id=update.message.message_id)
            return

        region = args[0].upper()
        uid = args[1]
        
        valid_regions =['IND', 'VN', 'BD', 'BR', 'ID', 'TH', 'SG', 'MY', 'PH', 'PK']
        if region not in valid_regions:
            await update.message.reply_text(sc(f"❌ Invalid region. Use one of: {', '.join(valid_regions)}"), reply_to_message_id=update.message.message_id)
            return
        
        if await check_user_permissions(update, context, "get", context.args):
            user_username = update.effective_user.username or "Unknown"
            await _execute_get_command(context, update.effective_chat.id, region, uid, user_username, update.message.message_id)

    except Exception as e:
        await update.message.reply_text(sc(f"⚠️ Error: {e}"), reply_to_message_id=update.message.message_id)

# ========= 👑 ADMIN COMMANDS 👑 =========
async def admin_only(update: Update) -> bool:
    if update.effective_user.id not in ADMIN_IDS: 
        await update.message.reply_text(sc("⛔ Unauthorized."), reply_to_message_id=update.message.message_id)
        return False
    return True

async def setvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    try:
        user_id, days = int(context.args[0]), int(context.args[1])
        vip_users[user_id] = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        save_vip_users(vip_users)
        await update.message.reply_text(sc(f"✅ VIP access granted to `{user_id}` for {days} days."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
    except (IndexError, ValueError): 
        await update.message.reply_text(sc("⚠️ Usage: `/setvip <user_id> <days>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def removevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    try:
        user_id = int(context.args[0])
        if user_id in vip_users:
            del vip_users[user_id]
            save_vip_users(vip_users)
            await update.message.reply_text(sc(f"✅ VIP access removed for `{user_id}`."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        else: 
            await update.message.reply_text(sc("❌ User is not a VIP."), reply_to_message_id=update.message.message_id)
    except (IndexError, ValueError): 
        await update.message.reply_text(sc("⚠️ Usage: `/removevip <user_id>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def viplist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    if not vip_users: 
        await update.message.reply_text(sc("❌ No VIP users found."), reply_to_message_id=update.message.message_id)
        return
    
    text = sc("🌟 **VIP Users List:**\n")
    for user_id, expiry in vip_users.items():
        text += sc(f"\n👑 `{user_id}` - Expires: `{expiry.strftime('%Y-%m-%d')}`")
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    gid = int(context.args[0]) if context.args else update.effective_chat.id
    allowed_groups.add(gid)
    save_allowed_groups(allowed_groups)
    await update.message.reply_text(sc(f"✅ Group `{gid}` allowed."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    gid = int(context.args[0]) if context.args else update.effective_chat.id
    allowed_groups.discard(gid)
    save_allowed_groups(allowed_groups)
    await update.message.reply_text(sc(f"❌ Group `{gid}` removed."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update): return
    if not context.args: 
        await update.message.reply_text(sc("⚠️ Usage: `/broadcast <message>`"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)
        return
    
    msg = await update.message.reply_text(sc("📢 Broadcasting..."), reply_to_message_id=update.message.message_id)
    sent, failed = 0, 0
    all_chat_ids = set(int(uid) for uid in user_data.keys()).union(allowed_groups)
    for chat_id in all_chat_ids:
        try: 
            await context.bot.send_message(chat_id, sc(" ".join(context.args)))
            sent += 1
        except Exception: 
            failed += 1
        await asyncio.sleep(0.05)
    await msg.edit_text(sc(f"📢 Broadcast Complete!\n✅ Sent: {sent}\n❌ Failed: {failed}"))

async def userinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update):
        return

    target_user_id = None

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        target_user_id = int(context.args[0])

    if not target_user_id:
        await update.message.reply_text(
            sc("⚠️ Usage:\n"
            "• Reply to a user: /userinfo\n"
            "• Provide ID: /userinfo <user_id>"),
            reply_to_message_id=update.message.message_id
        )
        return

    try:
        user = await context.bot.get_chat(target_user_id)
        user_id_str = str(target_user_id)

        safe_name = html.escape(user.full_name)

        if user.username:
            name_display = f'<a href="https://t.me/{user.username}">{safe_name}</a>'
            username_display = f"@{user.username}"
        else:
            name_display = f'<a href="tg://user?id={user.id}">{safe_name}</a>'
            username_display = "No username"

        if is_vip(target_user_id):
            expiry = vip_users.get(target_user_id)
            if expiry:
                vip_expiry = expiry.strftime("%Y-%m-%d %H:%M:%S")
                vip_status = f"✅ VIP (Expires: {vip_expiry})"
            else:
                vip_status = "✅ VIP"
        else:
            vip_status = "❌ Not VIP"

        if target_user_id == OWNER_ID:
            admin_status = "👑 OWNER"
        elif is_admin(target_user_id):
            admin_status = "✅ ADMIN"
        else:
            admin_status = "❌ Not Admin"

        reset_user_if_needed(target_user_id)
        user_stats = user_data.get(user_id_str, {})
        counts = user_stats.get('counts', {})
        verified_date = user_stats.get('verified_date', 'Never')
        reset_date = user_stats.get('reset_date', 'Never')

        safe_requester = html.escape(update.effective_user.full_name)

        if update.effective_user.username:
            requested_by = f'<a href="https://t.me/{update.effective_user.username}">{safe_requester}</a>'
        else:
            requested_by = f'<a href="tg://user?id={update.effective_user.id}">{safe_requester}</a>'

        info_text = sc(
            f"👤 <b>USER INFORMATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>User ID:</b> {user.id}\n"
            f"📛 <b>Name:</b> {name_display}\n"
            f"🔗 <b>Username:</b> {username_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 <b>Admin Status:</b> {admin_status}\n"
            f"💎 <b>VIP Status:</b> {vip_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>DAILY USAGE STATS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👍 Likes: {counts.get('like', 0)}/{USER_LIMITS['like']}\n"
            f"👀 Visits: {counts.get('visit', 0)}/{USER_LIMITS['visit']}\n"
            f"🔥 Spam: {counts.get('spam', 0)}/{USER_LIMITS['spam']}\n"
            f"📋 Get Info: {counts.get('get', 0)}/{USER_LIMITS['get']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 <b>Verified Date:</b> {verified_date}\n"
            f"🔄 <b>Reset Date:</b> {reset_date}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔰 <b>Requested by:</b> {requested_by}"
        )

        await update.message.reply_text(
            info_text,
            parse_mode="HTML",
            reply_to_message_id=update.message.message_id,
            disable_web_page_preview=True
        )

        logger.info(f"Admin {update.effective_user.id} checked info for user {target_user_id}")

    except Exception as e:
        logger.error(f"Error in userinfo command: {e}")
        await update.message.reply_text(
            sc(f"❌ Error: {html.escape(str(e))}"),
            reply_to_message_id=update.message.message_id
        )

async def stopverify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global verification_enabled
    if not await admin_only(update): return
    verification_enabled = False
    await update.message.reply_text(sc("🚫 Verification system has been *disabled*. Now commands will run directly."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def verifystatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = sc("✅ Enabled") if verification_enabled else sc("🚫 Disabled")
    await update.message.reply_text(sc(f"🔎 Verification system is currently: {status}"), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

async def bot_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not await admin_only(update): return
    bot_enabled = True
    await update.message.reply_text(sc("✅ Bot is now turned ON."), reply_to_message_id=update.message.message_id)

async def bot_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not await admin_only(update): return
    bot_enabled = False
    await update.message.reply_text(sc("🚫 Bot is now turned OFF."), reply_to_message_id=update.message.message_id)
    
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(sc("❌ Only Owner Can Give Admin To Others!"))
        return

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try: target_id = int(context.args[0])
        except: pass

    if target_id and target_id not in ADMIN_IDS:
        ADMIN_IDS.append(target_id)
        await update.message.reply_text(sc(f"✅ User {target_id} Is Now Admin."))
    else:
        await update.message.reply_text(sc("⚠️ User Id Is Wrong Or This Person Is Already Admin."))

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(sc("❌ Only Main Owner Can Remove Admins!"))
        return

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try: target_id = int(context.args[0])
        except: pass

    if target_id == OWNER_ID:
        await update.message.reply_text(sc("❌ Why Would I Remove Main Admin 🤔!"))
        return

    if target_id in ADMIN_IDS:
        ADMIN_IDS.remove(target_id)
        await update.message.reply_text(sc(f"✅ Admin access removed for {target_id}."))
    else:
        await update.message.reply_text(sc("❌ This User Is Not An Admin."))
        
async def startverify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global verification_enabled
    if not await admin_only(update): return
    verification_enabled = True
    await update.message.reply_text(sc("✅ Verification system has been *enabled*. Users must verify before using commands."), parse_mode=ParseMode.MARKDOWN, reply_to_message_id=update.message.message_id)

# ========= 🔄 DAILY RESET TASK 🔄 =========
async def daily_reset_task(app: Application):
    while True:
        now = datetime.datetime.now(timezone(RESET_TIMEZONE))
        reset_time = now.replace(hour=RESET_HOUR, minute=RESET_MINUTE, second=0, microsecond=0)
        if now >= reset_time: 
            reset_time += datetime.timedelta(days=1)
        await asyncio.sleep((reset_time - now).total_seconds())
        try: 
            await app.bot.send_message(OWNER_ID, sc("✅ Daily reset completed."))
        except Exception as e: 
            logger.error(f"Failed to send reset confirmation: {e}")
        logger.info("Daily reset task has run.")

# ========= AUTO LIKE SCHEDULED TASK =========
async def scheduled_autolike_task(app: Application):
    """Run autolike every 6 hours"""
    while True:
        await asyncio.sleep(60)
        
        while True:
            if bot_enabled:
                await execute_autolike_cycle(app)
            await asyncio.sleep(21600)

# ========= 🚀 MAIN FUNCTION 🚀 =========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("get", get_command))
    app.add_handler(CommandHandler("like", like))
    app.add_handler(CommandHandler("visit", visit))
    app.add_handler(CommandHandler("spam", spam))
    
    # Auto Like Commands
    app.add_handler(CommandHandler("auto", auto_command))
    app.add_handler(CommandHandler("removeauto", removeauto_command))
    app.add_handler(CommandHandler("autolist", autolist_command))
    app.add_handler(CommandHandler("autolog", autolog_command))
    
    # Admin Commands
    app.add_handler(CommandHandler("setvip", setvip))
    app.add_handler(CommandHandler("removevip", removevip))
    app.add_handler(CommandHandler("viplist", viplist))
    app.add_handler(CommandHandler("allow", allow))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("userinfo", userinfo_command))
    app.add_handler(CommandHandler("stopverify", stopverify))
    app.add_handler(CommandHandler("startverify", startverify))
    app.add_handler(CommandHandler("verifystatus", verifystatus))
    app.add_handler(CommandHandler("on", bot_on))
    app.add_handler(CommandHandler("off", bot_off))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    
    app.add_handler(CallbackQueryHandler(handle_join_verification_callback))

    loop = asyncio.get_event_loop()
    loop.create_task(daily_reset_task(app))
    loop.create_task(scheduled_autolike_task(app))

    logger.info("🤖 Bot is starting up...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()