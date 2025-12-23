import os
import json
import logging
import asyncio
import random
import string
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import BadRequest, ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
import zipfile
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import threading
import aiofiles
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration from environment variables
API_ID = int(os.getenv("API_ID", "24168862"))
API_HASH = os.getenv("API_HASH", "916a9424dd1e58ab7955001ccc0172b3")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8275315149:AAG4rS7B6PVw1LmsKt82urYIjA_FzSdMPBQ")

ADMIN_ID = int(os.getenv("ADMIN_ID", "6421770811"))
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "-1002023049910"))

MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb+srv://jaydipmore74:xCpTm5OPAfRKYnif@cluster0.5jo18.mongodb.net/?retryWrites=true&w=majority")

# Forced channel subscription
MUST_JOIN = -1002387668895  # ZeeMusicUpdate channel ID
MUST_JOIN_LINK = "https://t.me/ZeeMusicUpdate"

logger.info("Configuration loaded from environment variables.")

logger.info("Connecting to your Mongo Database...")
try:
    mongo_async = AsyncIOMotorClient(MONGO_DB_URI)
    mongodb = mongo_async.Anon
    logger.info("Connected to your Mongo Database.")
except Exception as e:
    logger.error(f"Failed to connect to your Mongo Database: {e}")
    exit()

# Initialize the bot
app = Client("session_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Collections
users_collection = mongodb.users
sessions_collection = mongodb.sessions
countries_collection = mongodb.countries
prices_collection = mongodb.prices
admins_collection = mongodb.admins
agents_collection = mongodb.agents
stats_collection = mongodb.stats
redeem_codes_collection = mongodb.redeem_codes
active_otp_listeners_collection = mongodb.active_otp_listeners
deposit_requests_collection = mongodb.deposit_requests
sell_logs_collection = mongodb.sell_logs
assigned_sessions_collection = mongodb.assigned_sessions
gmail_accounts_collection = mongodb.gmail_accounts
whatsapp_accounts_collection = mongodb.whatsapp_accounts
gmail_prices_collection = mongodb.gmail_prices
whatsapp_prices_collection = mongodb.whatsapp_prices

# Initialize countries with your list
INITIAL_COUNTRIES = {
    "sierra_leone": {"name": "Sierra Leone", "flag": "🇸🇱", "price": 80},
    "nepal": {"name": "Nepal", "flag": "🇳🇵", "price": 60},
    "vietnam": {"name": "Vietnam", "flag": "🇻🇳", "price": 70},
    "algeria": {"name": "Algeria", "flag": "🇩🇿", "price": 75},
    "afghanistan": {"name": "Afghanistan", "flag": "🇦🇫", "price": 65},
    "angola": {"name": "Angola", "flag": "🇦🇴", "price": 70},
    "australia": {"name": "Australia", "flag": "🇦🇺", "price": 100},
    "bangladesh": {"name": "Bangladesh", "flag": "🇧🇩", "price": 55},
    "chile": {"name": "Chile", "flag": "🇨🇱", "price": 85},
    "china": {"name": "China", "flag": "🇨🇳", "price": 90},
    "cote_divoire": {"name": "Côte d'Ivoire", "flag": "🇨🇮", "price": 75},
    "egypt": {"name": "Egypt", "flag": "🇪🇬", "price": 80},
    "ecuador": {"name": "Ecuador", "flag": "🇪🇨", "price": 75},
    "ethiopia": {"name": "Ethiopia", "flag": "🇪🇹", "price": 65},
    "israel": {"name": "Israel", "flag": "🇮🇱", "price": 95},
    "kenya": {"name": "Kenya", "flag": "🇰🇪", "price": 70},
    "mauritania": {"name": "Mauritania", "flag": "🇲🇷", "price": 75},
    "pakistan": {"name": "Pakistan", "flag": "🇵🇰", "price": 60},
    "greenland": {"name": "Greenland", "flag": "🇬🇱", "price": 110},
    "san_marino": {"name": "San Marino", "flag": "🇸🇲", "price": 120},
    "south_africa": {"name": "South Africa", "flag": "🇿🇦", "price": 85},
    "venezuela": {"name": "Venezuela", "flag": "🇻🇪", "price": 80},
    "sri_lanka": {"name": "Sri Lanka", "flag": "🇱🇰", "price": 65},
    "burkina_faso": {"name": "Burkina Faso", "flag": "🇧🇫", "price": 70}
}

# Initialize database collections
async def initialize_database():
    try:
        # Initialize countries with proper document structure
        existing_countries = await countries_collection.find_one({})
        if not existing_countries:
            countries_doc = {"data": INITIAL_COUNTRIES}
            await countries_collection.insert_one(countries_doc)
            logger.info("✅ Countries collection initialized")
        
        # Initialize prices with proper document structure
        existing_prices = await prices_collection.find_one({})
        if not existing_prices:
            prices_data = {country: data["price"] for country, data in INITIAL_COUNTRIES.items()}
            prices_doc = {"data": prices_data}
            await prices_collection.insert_one(prices_doc)
            logger.info("✅ Prices collection initialized")
        
        # Initialize stats
        existing_stats = await stats_collection.find_one({})
        if not existing_stats:
            await stats_collection.insert_one({
                "total_sold": 0,
                "today_sold": 0,
                "total_revenue": 0,
                "today_revenue": 0,
                "last_reset": str(datetime.now().date())
            })
            logger.info("✅ Stats collection initialized")
        
        # Initialize admins
        existing_admins = await admins_collection.find_one({})
        if not existing_admins:
            await admins_collection.insert_one({"admins": [ADMIN_ID]})
            logger.info("✅ Admins collection initialized")
        
        # Initialize agents
        existing_agents = await agents_collection.find_one({})
        if not existing_agents:
            await agents_collection.insert_one({"agents": []})
            logger.info("✅ Agents collection initialized")
        
        # Initialize referral credit
        existing_settings = await mongodb.settings.find_one({})
        if not existing_settings:
            await mongodb.settings.insert_one({"referral_credit": 50})
            logger.info("✅ Settings collection initialized")
            
        logger.info("🎉 Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")

# Helper functions
def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_redeem_code(length=12):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def reset_daily_stats():
    """Reset daily stats if date changed"""
    try:
        stats = await stats_collection.find_one({})
        today = str(datetime.now().date())
        if stats and stats.get("last_reset") != today:
            await stats_collection.update_one({}, {
                "$set": {
                    "today_sold": 0,
                    "today_revenue": 0,
                    "last_reset": today
                }
            })
    except Exception as e:
        logger.error(f"Error resetting daily stats: {e}")

async def is_admin(user_id):
    """Check if user is admin"""
    try:
        admins_data = await admins_collection.find_one({})
        return admins_data and user_id in admins_data.get("admins", [ADMIN_ID])
    except Exception as e:
        logger.error(f"Error checking admin: {e}")
        return False

async def is_agent(user_id):
    """Check if user is agent"""
    try:
        agents_data = await agents_collection.find_one({})
        return agents_data and user_id in agents_data.get("agents", [])
    except Exception as e:
        logger.error(f"Error checking agent: {e}")
        return False

async def is_admin_or_agent(user_id):
    """Check if user is admin or agent"""
    return await is_admin(user_id) or await is_agent(user_id)

async def send_to_log_group(text: str, reply_markup=None):
    """Send message to log group"""
    try:
        await app.send_message(LOG_GROUP_ID, text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending to log group: {e}")

async def get_user(user_id):
    """Get user from database"""
    try:
        user = await users_collection.find_one({"user_id": str(user_id)})
        if not user:
            # Create new user
            user_data = {
                "user_id": str(user_id),
                "balance": 0,
                "referral_code": f"ref_{user_id}",
                "referrals": [],
                "total_spent": 0,
                "joined_date": str(datetime.now()),
                "current_phone": None,
                "otp_waiting": False,
                "total_earned": 0
            }
            await users_collection.insert_one(user_data)
            return user_data
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        # Return default user data if error
        return {
            "user_id": str(user_id),
            "balance": 0,
            "referral_code": f"ref_{user_id}",
            "referrals": [],
            "total_spent": 0,
            "joined_date": str(datetime.now()),
            "current_phone": None,
            "otp_waiting": False,
            "total_earned": 0
        }

async def update_user(user_id, update_data):
    """Update user in database"""
    try:
        await users_collection.update_one(
            {"user_id": str(user_id)},
            {"$set": update_data},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error updating user: {e}")

async def get_countries():
    """Get all countries"""
    try:
        countries_doc = await countries_collection.find_one({})
        if countries_doc and "data" in countries_doc:
            return countries_doc["data"]
        return INITIAL_COUNTRIES
    except Exception as e:
        logger.error(f"Error getting countries: {e}")
        return INITIAL_COUNTRIES

async def get_sessions(country_code):
    """Get sessions for a country"""
    try:
        sessions_data = await sessions_collection.find_one({"country": country_code})
        return sessions_data.get("sessions", []) if sessions_data else []
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return []

async def update_sessions(country_code, sessions_list):
    """Update sessions for a country"""
    try:
        await sessions_collection.update_one(
            {"country": country_code},
            {"$set": {"sessions": sessions_list}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error updating sessions: {e}")

async def get_stats():
    """Get bot statistics"""
    try:
        stats = await stats_collection.find_one({})
        return stats or {
            "total_sold": 0,
            "today_sold": 0,
            "total_revenue": 0,
            "today_revenue": 0,
            "last_reset": str(datetime.now().date())
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "total_sold": 0,
            "today_sold": 0,
            "total_revenue": 0,
            "today_revenue": 0,
            "last_reset": str(datetime.now().date())
        }

async def update_stats(update_data):
    """Update bot statistics"""
    try:
        await stats_collection.update_one({}, {"$set": update_data}, upsert=True)
    except Exception as e:
        logger.error(f"Error updating stats: {e}")

async def get_prices():
    """Get all prices"""
    try:
        prices_doc = await prices_collection.find_one({})
        if prices_doc and "data" in prices_doc:
            return prices_doc["data"]
        return {country: data["price"] for country, data in INITIAL_COUNTRIES.items()}
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        return {country: data["price"] for country, data in INITIAL_COUNTRIES.items()}

async def update_prices(prices_data):
    """Update prices"""
    try:
        await prices_collection.update_one({}, {"$set": {"data": prices_data}}, upsert=True)
    except Exception as e:
        logger.error(f"Error updating prices: {e}")

async def update_countries(countries_data):
    """Update countries"""
    try:
        await countries_collection.update_one({}, {"$set": {"data": countries_data}}, upsert=True)
    except Exception as e:
        logger.error(f"Error updating countries: {e}")

# Telethon OTP Listener Class
class OTPListener:
    def __init__(self, session_path, user_id, phone_number):
        self.session_path = session_path
        self.user_id = user_id
        self.phone_number = phone_number
        self.client = None
        self.otp_received = None
        self.is_listening = False

    async def start_listening(self):
        """Start listening for OTP using Telethon"""
        try:
            logger.info(f"Starting OTP listener for {self.phone_number}")
            self.client = TelegramClient(
                self.session_path,
                API_ID,
                API_HASH
            )

            @self.client.on(events.NewMessage(from_users=777000))
            async def handler(event):
                message = event.message.text or ""
                logger.info(f"Message from 777000: {message}")
                
                # Look for OTP in message
                otp_match = re.search(r'\b\d{5}\b', message)
                if otp_match:
                    self.otp_received = otp_match.group(0)
                    logger.info(f"OTP found: {self.otp_received} for {self.phone_number}")
                    
                    # Send OTP to user via Pyrogram bot
                    try:
                        await app.send_message(
                            chat_id=int(self.user_id),
                            text=f"""✅ ᴏᴛᴘ ʀᴇᴄᴇɪᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ..!! ☠️

📞 ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ: {self.phone_number}

🔢 ᴏᴛᴘ ᴄᴏᴅᴇ: {self.otp_received}

💡 ᴜsᴇ ᴛʜɪs ᴏᴛᴘ ғᴏʀ ᴀᴄᴄᴏᴜɴᴛ ʟᴏɢɪɴ 👌""",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🛒 ʙᴜʏ ᴍᴏʀᴇ ᴀᴄᴄᴏᴜɴᴛs", callback_data="buy_account")],
                                [InlineKeyboardButton("👤 ᴘʀᴏғɪʟᴇ", callback_data="profile")]
                            ])
                        )
                        # Stop listening after OTP received
                        await self.stop_listening()
                    except Exception as e:
                        logger.error(f"Error sending OTP to user: {e}")

            await self.client.start()
            self.is_listening = True
            
            # Store in database
            await active_otp_listeners_collection.update_one(
                {"phone_number": self.phone_number},
                {"$set": {
                    "user_id": self.user_id,
                    "started_at": str(datetime.now())
                }},
                upsert=True
            )
            
            logger.info(f"OTP listener started successfully for {self.phone_number}")
            # keep the client connected in background
            asyncio.create_task(self.client.run_until_disconnected())
            return True
        except Exception as e:
            logger.error(f"Error starting OTP listener: {e}")
            return False

    async def stop_listening(self):
        """Stop the OTP listener"""
        try:
            if self.client:
                await self.client.disconnect()
            self.is_listening = False
            
            # Remove from database
            await active_otp_listeners_collection.delete_one({"phone_number": self.phone_number})
            logger.info(f"OTP listener stopped for {self.phone_number}")
        except Exception as e:
            logger.error(f"Error stopping OTP listener: {e}")

# Global dictionary to store active listeners
active_listeners = {}

# Ensure directories exist
for directory in ["sessions", "temp"]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Start command with referral support (force subscription check integrated inside)
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = str(message.from_user.id)
    
    # Check channel membership first
    if MUST_JOIN and MUST_JOIN != "ZeeMusicUpdate":
        try:
            await app.get_chat_member(MUST_JOIN, message.from_user.id)
        except UserNotParticipant:
            # User not in channel - block start command
            link = MUST_JOIN_LINK
            try:
                await message.reply_photo(
                    photo="bot_assets/start_image.png",
                    caption=f"๏ ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴛʜᴇ [ᴄʜᴀɴɴᴇʟ]({link}) ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ!\n\nᴊᴏɪɴ ᴀɴᴅ ᴛʏᴘᴇ /start ᴀɢᴀɪɴ",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("• ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ •", url=link)],
                        [InlineKeyboardButton("• ᴀʟᴛᴇʀɴᴀᴛᴇ •", url="https://t.me/+wZDbepGf4KlhOGI1")]
                    ])
                )
            except Exception as e:
                logger.error(f"Could not send join message: {e}")
            return
        except Exception as e:
            logger.error(f"Channel check failed: {e}")
            return
    
    await reset_daily_stats()

    # Check for referral
    settings = await mongodb.settings.find_one({})
    referral_bonus = settings.get("referral_credit", 50) if settings else 50
    referred_by = None
    
    if len(message.command) > 1:
        ref_code = message.command[1]
        if ref_code.startswith("ref_"):
            ref_user_id = ref_code[4:]
            ref_user = await users_collection.find_one({"user_id": ref_user_id})
            if ref_user and ref_user_id != user_id:
                referred_by = ref_user_id

    # Initialize user in database if not exists
    user = await get_user(user_id)
    is_new_user = user.get("joined_date") == str(datetime.now())
    
    # Log to admin group
    username = message.from_user.username or "No Username"
    first_name = message.from_user.first_name or "User"
    profile_link = f"tg://user?id={message.from_user.id}"
    
    log_text = f"""
🆕 **NEW USER STARTED BOT**

👤 **User Info:**
• Name: {first_name}
• Username: @{username if username != 'No Username' else 'N/A'}
• ID: `{user_id}`
• [Profile]({profile_link})

📊 **Details:**
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    if referred_by:
        log_text += f"• Referred By: `{referred_by}`\n"
    
    try:
        await send_to_log_group(log_text)
    except Exception as e:
        logger.error(f"Error logging to group: {e}")
    
    # Add referral bonus if applicable
    if referred_by:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": referral_bonus}}
        )
        await users_collection.update_one(
            {"user_id": referred_by},
            {"$inc": {"balance": referral_bonus, "total_earned": referral_bonus},
             "$push": {"referrals": user_id}}
        )
        
        # Send notification to referrer
        try:
            await app.send_message(
                int(referred_by),
                f"ᴄᴏɴɢʀᴀʟᴜʟᴀᴛɪᴏɴ 🎉 ʏᴏᴜ ᴇᴀʀɴᴇᴅ {referral_bonus} ᴄʀᴇᴅɪᴅs 🤑 {message.from_user.first_name} ᴊᴏɪɴᴇᴅ ᴜsɪɴɢ ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟ ʟɪɴᴋ joined."
            )
        except:
            pass

    welcome_text = """● ʜᴇʟʟᴏ ʙᴀʙᴜ ᴡᴇʟᴄᴏᴍᴇ... 💫

•──────────────────────•
❖ ʙᴜʏ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛs ᴡɪᴛʜ ɪɴsᴛᴀɴᴛ ᴏᴛᴘ.
❖ ᴇᴀʀɴ ᴄʀᴇᴅɪᴛ ᴛʜʀᴏᴜɢʜ ʀᴇғᴇʀʀᴀʟs.
❖ ғᴀsᴛ ᴀɴᴅ ʀᴇʟɪᴀʙʟᴇ sᴇʀᴠɪᴄᴇ.
❖ ᴀʟᴡᴀʏs ᴛᴏᴘ ϙᴜᴀʟɪᴛʏ ᴀᴄᴄᴏᴜɴᴛs
•──────────────────────"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Telegram", callback_data="buy_account"), InlineKeyboardButton("💌 Gmail", callback_data="buy_gmail"), InlineKeyboardButton("💬 WhatsApp", callback_data="buy_whatsapp")],
        [InlineKeyboardButton("👥 REFER", callback_data="refer_earn"), InlineKeyboardButton("🎫 REDEEM", callback_data="redeem_code")],
        [InlineKeyboardButton("💳 DEPOSIT", callback_data="deposit_money"), InlineKeyboardButton("👤 PROFILE", callback_data="profile")],
        [InlineKeyboardButton("📖 HOW TO", callback_data="how_to_use")],
        [InlineKeyboardButton("💬 SUPPORT 1", url="https://t.me/+wZDbepGf4KlhOGI1"), InlineKeyboardButton("🎵 SUPPORT 2", url="https://t.me/ZeeMusicUpdate")]
    ])
    
    try:
        await message.reply_photo(
            photo="bot_assets/start_image.png",
            caption=welcome_text,
            reply_markup=keyboard
        )
    except BadRequest:
        await message.reply_text(welcome_text, reply_markup=keyboard)

# ==================== ENHANCED ADMIN COMMANDS ====================

@app.on_message(filters.command("addcountry"))
async def add_country(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 4:
        await message.reply_text("❌ Usage: /addcountry <country_code> <country_name> <price>\n💡 Example: /addcountry usa \"United States\" 100")
        return

    country_code = message.command[1].lower()
    country_name = message.command[2]
    try:
        price = int(message.command[3])
    except:
        await message.reply_text("❌ Invalid price amount")
        return

    # Add country to database
    countries_data = await get_countries()
    countries_data[country_code] = {
        "name": country_name,
        "flag": "🇺🇳",
        "price": price
    }
    await update_countries(countries_data)
    
    # Update prices
    prices_data = await get_prices()
    prices_data[country_code] = price
    await update_prices(prices_data)

    await message.reply_text(f"✅ Country added: {country_name} ({country_code}) - {price} credits")

@app.on_message(filters.command("removecountry"))
async def remove_country(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /removecountry <country_code>")
        return

    country_code = message.command[1].lower()
    countries_data = await get_countries()
    
    if country_code in countries_data:
        del countries_data[country_code]
        await update_countries(countries_data)
        
        # Remove from prices
        prices_data = await get_prices()
        if country_code in prices_data:
            del prices_data[country_code]
            await update_prices(prices_data)
        
        await message.reply_text(f"✅ Country removed: {country_code}")
    else:
        await message.reply_text("❌ Country not found!")

@app.on_message(filters.command("addadmin"))
async def add_admin(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("❌ Owner access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /addadmin <user_id>")
        return

    try:
        new_admin = int(message.command[1])
        admins_data = await admins_collection.find_one({})
        admins_list = admins_data.get("admins", [ADMIN_ID]) if admins_data else [ADMIN_ID]
        
        if new_admin not in admins_list:
            admins_list.append(new_admin)
            await admins_collection.update_one({}, {"$set": {"admins": admins_list}}, upsert=True)
            await message.reply_text(f"✅ Admin added: {new_admin}")
        else:
            await message.reply_text("❌ User is already admin!")
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("addagent"))
async def add_agent(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /addagent <user_id>")
        return

    try:
        new_agent = int(message.command[1])
        agents_data = await agents_collection.find_one({})
        agents_list = agents_data.get("agents", []) if agents_data else []
        
        if new_agent not in agents_list:
            agents_list.append(new_agent)
            await agents_collection.update_one({}, {"$set": {"agents": agents_list}}, upsert=True)
            await message.reply_text(f"✅ Agent added: {new_agent}\n\n🔧 Agent Powers:\n• View stock (/stock)\n• Upload sessions (/upload)")
            
            # Notify the new agent
            try:
                await app.send_message(
                    new_agent,
                    f"🎉 ʏᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴀᴅᴅᴇᴅ ᴀs ᴀɴ ᴀɴ ᴀɢᴇɴᴛ!\n\n✅ ʏᴏᴜ ᴄᴀɴ ɴᴏᴡ:\n• ᴠɪᴇᴡ sᴛᴏᴄᴋ: /stock\n• ᴜᴘʟᴏᴀᴅ sᴇssɪᴏɴs: /upload <country>"
                )
            except:
                pass
                
            # Log to group
            await send_to_log_group(f"👤 New Agent Added: {new_agent} by {message.from_user.first_name}")
        else:
            await message.reply_text("❌ User is already an agent!")
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("rmagent"))
async def remove_agent(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /rmagent <user_id>")
        return

    try:
        agent_id = int(message.command[1])
        agents_data = await agents_collection.find_one({})
        agents_list = agents_data.get("agents", []) if agents_data else []
        
        if agent_id in agents_list:
            agents_list.remove(agent_id)
            await agents_collection.update_one({}, {"$set": {"agents": agents_list}}, upsert=True)
            await message.reply_text(f"✅ Agent removed: {agent_id}")
            
            # Notify the removed agent
            try:
                await app.send_message(
                    agent_id,
                    "⚠️ Your agent access has been removed."
                )
            except:
                pass
                
            # Log to group
            await send_to_log_group(f"🚫 Agent Removed: {agent_id} by {message.from_user.first_name}")
        else:
            await message.reply_text("❌ User is not an agent!")
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("agents"))
async def list_agents(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    agents_data = await agents_collection.find_one({})
    agents_list = agents_data.get("agents", []) if agents_data else []
    
    if not agents_list:
        await message.reply_text("❌ No agents found!")
        return
    
    text = "👥 **ACTIVE AGENTS**\n\n"
    for idx, agent_id in enumerate(agents_list, 1):
        text += f"{idx}. ID: `{agent_id}`\n"
    
    text += f"\n📊 Total Agents: {len(agents_list)}"
    text += "\n\n🔧 Agent Powers:\n• View stock (/stock)\n• Upload sessions (/upload)"
    
    await message.reply_text(text)

@app.on_message(filters.command("removecredit"))
async def remove_credit(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /removecredit <user_id> <amount>")
        return

    try:
        user_id = str(message.command[1])
        amount = int(message.command[2])
        user = await get_user(user_id)
        
        if user["balance"] >= amount:
            await users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": -amount}}
            )
            await message.reply_text(f"✅ Removed {amount} credits from user {user_id}")
            
            # Notify user
            try:
                await app.send_message(
                    int(user_id),
                    f"⚠️ Admin removed {amount} credits from your account."
                )
            except:
                pass
        else:
            await message.reply_text("❌ User doesn't have enough credits!")
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("upload"))
async def upload_session(client, message: Message):
    # Check if user is admin or agent
    if not await is_admin_or_agent(message.from_user.id):
        await message.reply_text("❌ Admin or Agent access required!")
        return
        
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("❌ Please reply to a zip or .session file with /upload <country>")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /upload <country>")
        return

    country = message.command[1].lower()
    countries_data = await get_countries()
    if country not in countries_data:
        await message.reply_text(f"❌ Invalid country. Use /addcountry first")
        return

    file = message.reply_to_message.document
    if not (file.file_name.endswith('.zip') or file.file_name.endswith('.session')):
        await message.reply_text("❌ Please upload .zip or .session files only")
        return

    # Download file
    download_path = await message.reply_to_message.download()
    
    try:
        if file.file_name.endswith('.zip'):
            # Extract zip file
            extract_path = f"sessions/{country}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            # Process extracted session files
            session_files = []
            for root, dirs, files in os.walk(extract_path):
                for file_name in files:
                    if file_name.endswith('.session'):
                        phone_match = re.search(r'\+\d+', file_name)
                        phone_number = phone_match.group(0) if phone_match else "Unknown"
                        session_data = {
                            "file_path": os.path.join(root, file_name),
                            "file_name": file_name,
                            "phone_number": phone_number,
                            "uploaded_at": str(datetime.now()),
                            "country": country
                        }
                        session_files.append(session_data)

            # Add to database
            existing_sessions = await get_sessions(country)
            existing_sessions.extend(session_files)
            await update_sessions(country, existing_sessions)
            
            await message.reply_text(f"✅ Uploaded {len(session_files)} session files to {country}!")
            
            # Log to group
            uploader_type = "Admin" if await is_admin(message.from_user.id) else "Agent"
            await send_to_log_group(f"📤 {uploader_type} {message.from_user.first_name} uploaded {len(session_files)} sessions to {country}")
        else:
            # Single session file
            phone_match = re.search(r'\+\d+', file.file_name)
            phone_number = phone_match.group(0) if phone_match else "Unknown"
            
            # Move file to sessions directory
            new_path = f"sessions/{file.file_name}"
            os.rename(download_path, new_path)
            
            session_data = {
                "file_path": new_path,
                "file_name": file.file_name,
                "phone_number": phone_number,
                "uploaded_at": str(datetime.now()),
                "country": country
            }
            
            # Add to database
            existing_sessions = await get_sessions(country)
            existing_sessions.append(session_data)
            await update_sessions(country, existing_sessions)
            
            await message.reply_text(f"✅ Session file uploaded to {country}!\n📞 Phone: {phone_number}")
            
            # Log to group
            uploader_type = "Admin" if await is_admin(message.from_user.id) else "Agent"
            await send_to_log_group(f"📤 {uploader_type} {message.from_user.first_name} uploaded 1 session to {country} - {phone_number}")
    except Exception as e:
        await message.reply_text(f"❌ Error processing file: {str(e)}")

@app.on_message(filters.command("stock"))
async def stock_command(client, message: Message):
    # Allow both admins and agents to check stock
    if not await is_admin_or_agent(message.from_user.id):
        await message.reply_text("❌ Admin or Agent access required!")
        return

    countries_data = await get_countries()
    stock_text = "📊 **Current Stock:**\n\n"
    
    for country_code, country_data in countries_data.items():
        sessions = await get_sessions(country_code)
        count = len(sessions)
        prices_data = await get_prices()
        price = prices_data.get(country_code, country_data.get("price", 0))
        stock_text += f"{country_data.get('flag', '🇺🇳')} {country_data['name']}: {count} accounts - {price} credits\n"
    
    await message.reply_text(stock_text)

@app.on_message(filters.command("todaysell"))
async def todaysell_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    await reset_daily_stats()
    stats = await get_stats()
    
    text = f"""
📈 Today's Sales

🛒 Accounts Sold: {stats.get('today_sold', 0)}
💰 Revenue: {stats.get('today_revenue', 0)} credits
📅 Date: {stats.get('last_reset', 'Unknown')}
"""
    await message.reply_text(text)

@app.on_message(filters.command("stats"))
async def stats_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    await reset_daily_stats()
    stats = await get_stats()
    total_users = await users_collection.count_documents({})
    
    # Calculate total referral earnings
    pipeline = [
        {"$group": {"_id": None, "total_earned": {"$sum": "$total_earned"}}}
    ]
    result = await users_collection.aggregate(pipeline).to_list(length=1)
    total_ref_earnings = result[0]["total_earned"] if result else 0

    text = f"""
📊 Bot Statistics

👥 Total Users: {total_users}
🛒 Total Sold: {stats.get('total_sold', 0)}
💰 Total Revenue: {stats.get('total_revenue', 0)} credits
📅 Today's Sold: {stats.get('today_sold', 0)}
💳 Today's Revenue: {stats.get('today_revenue', 0)} credits
👥 Referral Earnings: {total_ref_earnings} credits
"""
    await message.reply_text(text)

@app.on_message(filters.command("setprice"))
async def setprice_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) != 3:
        await message.reply_text("❌ Usage: /setprice <country> <amount>")
        return

    country = message.command[1].lower()
    try:
        price = int(message.command[2])
    except ValueError:
        await message.reply_text("❌ Invalid price amount")
        return

    countries_data = await get_countries()
    if country not in countries_data:
        await message.reply_text(f"❌ Invalid country.")
        return

    # Update prices
    prices_data = await get_prices()
    prices_data[country] = price
    await update_prices(prices_data)
    
    # Update countries
    countries_data[country]["price"] = price
    await update_countries(countries_data)

    await message.reply_text(f"✅ Price for {countries_data[country]['name']} set to {price} credits")

@app.on_message(filters.command("gencode"))
async def gencode_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 4:
        await message.reply_text("❌ Usage: /gencode <max_uses> <amount> <valid_hours>")
        return

    try:
        max_uses = int(message.command[1])
        amount = int(message.command[2])
        valid_hours = int(message.command[3])
    except ValueError:
        await message.reply_text("❌ All parameters must be numbers")
        return

    code = generate_redeem_code()
    expiry_time = datetime.now() + timedelta(hours=valid_hours)
    
    redeem_data = {
        "code": code,
        "max_uses": max_uses,
        "used_count": 0,
        "amount": amount,
        "expiry": str(expiry_time),
        "created_by": message.from_user.id
    }
    
    await redeem_codes_collection.insert_one(redeem_data)

    text = f"""
🎫 Redeem Code Generated

📟 Code: {code}
💰 Amount: {amount} credits
👥 Max Uses: {max_uses}
⏰ Valid For: {valid_hours} hours
🕐 Expires: {expiry_time.strftime('%Y-%m-%d %H:%M')}
"""
    await message.reply_text(text)

@app.on_message(filters.command("updaterefercredit"))
async def update_refer_credit(client, message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("❌ Owner access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /updaterefercredit <amount>")
        return

    try:
        amount = int(message.command[1])
        await mongodb.settings.update_one({}, {"$set": {"referral_credit": amount}}, upsert=True)
        await message.reply_text(f"✅ Referral credit updated to {amount} credits")
    except:
        await message.reply_text("❌ Invalid amount!")

# ==================== NEW ADMIN COMMANDS ====================

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_command(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a message to broadcast")
        return

    users = await users_collection.find({}).to_list(length=None)
    total = len(users)
    success = 0
    failed = 0

    await message.reply_text(f"📢 Starting broadcast to {total} users...")

    for user in users:
        try:
            await message.reply_to_message.copy(int(user["user_id"]))
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)  # Prevent flooding

    await message.reply_text(f"✅ Broadcast completed!\n\n✅ Success: {success}\n❌ Failed: {failed}")

@app.on_message(filters.command("userinfo"))
async def user_info_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /userinfo <user_id>")
        return

    user_id = message.command[1]
    user = await get_user(user_id)

    text = f"""
👤 User Information

🆔 User ID: {user['user_id']}
💰 Balance: {user.get('balance', 0)} credits
💳 Total Spent: {user.get('total_spent', 0)} credits
👥 Referrals: {len(user.get('referrals', []))}
🎯 Referral Earnings: {user.get('total_earned', 0)} credits
📅 Joined: {user.get('joined_date', 'Unknown')}
"""
    await message.reply_text(text)

@app.on_message(filters.command("addcredit"))
async def add_credit_command(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /addcredit <user_id> <amount>")
        return

    try:
        user_id = message.command[1]
        amount = int(message.command[2])
        
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
        
        await message.reply_text(f"✅ Added {amount} credits to user {user_id}")
        
        # Notify user
        try:
            await app.send_message(
                int(user_id),
                f"🎉 Admin added {amount} credits to your account!"
            )
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# ==================== FIXED COUNTRY DISPLAY FUNCTIONS ====================

async def _sorted_countries_all():
    """Return list of (code, data) with stock>0 first, then the rest, both alphabetically by name."""
    try:
        countries_data = await get_countries()
        with_stock = []
        without_stock = []
        
        for country_code, country_data in countries_data.items():
            # Ensure country_data is a dictionary and has required keys
            if isinstance(country_data, dict) and 'name' in country_data:
                sessions = await get_sessions(country_code)
                count = len(sessions)
                if count > 0:
                    with_stock.append((country_code, country_data))
                else:
                    without_stock.append((country_code, country_data))
        
        # Sort both lists by country name
        with_stock.sort(key=lambda x: x[1]["name"].lower())
        without_stock.sort(key=lambda x: x[1]["name"].lower())
        
        return with_stock + without_stock
    except Exception as e:
        logger.error(f"Error in _sorted_countries_all: {e}")
        return []

async def show_countries(client, callback_query: CallbackQuery, page=0):
    try:
        # Show all countries, but stock ones first
        all_countries = await _sorted_countries_all()
        if not all_countries:
            await _safe_edit(callback_query, "❌ No countries configured yet.", [
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
            return

        items_per_page = 12
        total_pages = (len(all_countries) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages - 1))
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_countries = all_countries[start_idx:end_idx]
        
        keyboard = []
        row = []
        for country_code, country_data in page_countries:
            sessions = await get_sessions(country_code)
            available = len(sessions)
            suffix = "" if available > 0 else " (0)"
            button_text = f"{country_data.get('flag', '🇺🇳')} {country_data['name']}{suffix}"
            button = InlineKeyboardButton(
                button_text,
                callback_data=f"country_{country_code}"
            )
            row.append(button)
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Nav row
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ʙᴀᴄᴋ", callback_data=f"page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="none"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="main_menu")])

        await _safe_edit(
            callback_query,
            "🌍 **❍ sᴇʟᴇᴄᴛ ᴄᴏᴜɴᴛʀʏ**\n\n❖ ᴄᴏᴜɴᴛʀɪᴇs ᴡɪᴛʜ sᴛᴏᴄᴋ ᴀʀᴇ sʜᴏᴡɴ ғɪʀsᴛ",
            keyboard
        )
    except Exception as e:
        logger.error(f"Error showing countries: {e}")
        await callback_query.answer("❌ Error loading countries", show_alert=True)

async def _safe_edit(callback_query: CallbackQuery, text: str, keyboard_rows):
    """Edit caption if media, else edit text."""
    try:
        await callback_query.message.edit_caption(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard_rows)
        )
    except Exception:
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard_rows)
            )
        except Exception as e:
            logger.error(f"Error in _safe_edit: {e}")

async def show_countries_page(client, callback_query: CallbackQuery, page=0):
    await show_countries(client, callback_query, page)

async def show_country_info(client, callback_query: CallbackQuery, country_code):
    countries_data = await get_countries()
    if country_code not in countries_data:
        await callback_query.answer("❌ Country not found")
        return

    country_data = countries_data[country_code]
    sessions = await get_sessions(country_code)
    available_sessions = len(sessions)
    prices_data = await get_prices()
    price = prices_data.get(country_code, country_data.get("price", 0))
    
    text = f"""
{country_data.get('flag', '🇺🇳')} {country_data['name']} Accounts

💵 ᴘʀɪᴄᴇ: {price} credits

📱 ᴀᴠᴀɪʟᴀʙʟᴇ: {available_sessions} ᴀᴄᴄᴏᴜɴᴛs

⚡ ϙᴜᴀʟɪᴛʏ: ᴘʀɪᴍɪᴜᴍ+


ᴄʟɪᴄᴋ ʙᴜʏ ᴛᴏ ᴘᴜʀᴄʜᴀsᴇ ᴀᴄᴄᴏᴜɴᴛ.

"""

    keyboard = [
        [InlineKeyboardButton("🛒 ʙᴜʏ ɴᴏᴡ", callback_data=f"buy_{country_code}")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴄᴏᴜɴᴛʀɪᴇs.", callback_data="buy_account")]
    ]
    await _safe_edit(callback_query, text, keyboard)

# ==================== ENHANCED USER FEATURES ====================

@app.on_callback_query()
async def handle_callback(client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = str(callback_query.from_user.id)

    try:
        if data == "buy_account":
            await show_countries(client, callback_query)
        elif data == "buy_gmail":
            await buy_gmail_account(client, callback_query, user_id)
        elif data == "buy_whatsapp":
            await buy_whatsapp_account(client, callback_query, user_id)
        elif data.startswith("country_"):
            country_code = data.split("_", 1)[1]
            await show_country_info(client, callback_query, country_code)
        elif data.startswith("buy_"):
            country_code = data.split("_", 1)[1]
            await process_purchase(client, callback_query, country_code)
        elif data == "view_otp":
            await start_otp_listener(client, callback_query, user_id)
        elif data == "stop_otp":
            await stop_otp_listener(client, callback_query, user_id)
        elif data == "refer_earn":
            await show_refer_info(client, callback_query, user_id)
        elif data == "redeem_code":
            await show_redeem_info(client, callback_query)
        elif data == "deposit_money":
            await show_deposit_options(client, callback_query, user_id)
        elif data == "profile":
            await show_profile(client, callback_query, user_id)
        elif data == "how_to_use":
            how_to_use_text = """📖 HOW TO USE THIS BOT 📖

1️⃣ ʙᴜʏ ᴀᴄᴄᴏᴜɴᴛs:
   • Click "🛒 BUY ACCOUNTS" button
   • Select country you want
   • Click BUY NOW
   • Enter OTP when prompted

2️⃣ ɢᴇᴛ ᴏᴛᴘ:
   • After buying, click "VIEW OTP" 
   • Bot will listen for OTP code
   • OTP will be sent automatically

3️⃣ ᴇᴀʀɴ ᴄʀᴇᴅɪᴛs:
   • Share your referral link
   • Get 50 credits per referral
   • Use credits to buy more accounts

4️⃣ ᴅᴇᴘᴏsɪᴛ ᴄʀᴇᴅɪᴛs:
   • Click "💳 DEPOSIT"
   • Choose UPI or Crypto
   • Submit screenshot
   • Credits added after approval

5️⃣ ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs:
   • Click "🎫 REDEEM CODE"
   • Enter code from admin
   • Get instant credits

❓ Need Help? Join Support Groups!"""
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
            await _safe_edit(callback_query, how_to_use_text, keyboard)
        elif data == "main_menu":
            await go_to_main_menu(client, callback_query)
        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            await show_countries_page(client, callback_query, page)
        elif data == "deposit_upi":
            await show_upi_deposit(client, callback_query, user_id)
        elif data == "deposit_crypto":
            await show_crypto_deposit(client, callback_query, user_id)
        elif data == "submit_payment":
            await request_payment_screenshot(client, callback_query, user_id)
        elif data.startswith("approve_deposit_"):
            deposit_id = data.split("_", 2)[2]
            await approve_deposit(client, callback_query, deposit_id)
        elif data.startswith("reject_deposit_"):
            deposit_id = data.split("_", 2)[2]
            await reject_deposit(client, callback_query, deposit_id)
        elif data == "none":
            await callback_query.answer("•", show_alert=False)
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        await callback_query.answer("❌ Error processing request", show_alert=True)

async def process_purchase(client, callback_query: CallbackQuery, country_code):
    user_id = str(callback_query.from_user.id)
    user = await get_user(user_id)
    
    countries_data = await get_countries()
    country_data = countries_data.get(country_code, {})
    prices_data = await get_prices()
    price = prices_data.get(country_code, country_data.get("price", 0))

    # Check balance
    if user["balance"] < price:
        await callback_query.answer(f"❌ Insufficient balance! Need {price} credits", show_alert=True)
        return

    # Check if sessions available
    available_sessions = await get_sessions(country_code)
    if not available_sessions:
        await callback_query.answer("❌ No accounts available for this country", show_alert=True)
        return

    # Deduct balance and get session file
    await users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": -price, "total_spent": price}}
    )
    
    session_data = available_sessions.pop(0)
    await update_sessions(country_code, available_sessions)

    # Update stats
    stats = await get_stats()
    await update_stats({
        "total_sold": stats.get("total_sold", 0) + 1,
        "today_sold": stats.get("today_sold", 0) + 1,
        "total_revenue": stats.get("total_revenue", 0) + price,
        "today_revenue": stats.get("today_revenue", 0) + price,
        "last_reset": stats.get("last_reset", str(datetime.now().date()))
    })

    # Set user's current phone for OTP
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "current_phone": session_data["phone_number"],
            "otp_waiting": True
        }}
    )

    # Keep purchased session for OTP
    await assigned_sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": session_data},
        upsert=True
    )

    # Send phone number and instructions to user (NOT session file)
    try:
        await client.send_message(
            chat_id=callback_query.from_user.id,
            text=f"""
✅ ᴘᴜʀᴄʜᴀsᴇ sᴜᴄᴄᴇssғᴜʟl!

📱 ᴄᴏᴜᴜɴᴛʀʏ: {country_data.get('name', 'Unknown')}

📞 ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ: {session_data['phone_number']}

💵 ᴘʀɪᴄ: {price} credits

🕐 ᴛɪᴍᴇ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📲 ʟᴏɢɪɴ ɪɴsᴛʀᴜᴄᴛɪᴏɴs:

 ғᴏʀ ʟᴏɢɪɴ ᴄʟɪᴄᴋ ғɪʀsᴛ ᴏɴʟʏ ʟᴏɢɪɴ ʙᴜᴛᴛᴏɴ 
""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʟᴏɢɪɴ", callback_data="view_otp")],
                [InlineKeyboardButton("🛒 ʙᴜʏ ɴᴏᴡ", callback_data="buy_account")],
                [InlineKeyboardButton("👤 ᴘʀᴏғɪʟᴇ", callback_data="profile")]
            ])
        )

        await callback_query.answer("✅ Purchase successful! Check your messages.", show_alert=True)
        
        # Send sell log to group with session file
        log_text = f"""
🛒 ACCOUNT SOLD

👤 User: {callback_query.from_user.first_name} (ID: {user_id})
📱 Country: {country_data.get('name', 'Unknown')}
📞 Phone: {session_data['phone_number']}
💰 Price: {price} credits
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await send_to_log_group(log_text)
        
        # Send session file to log group
        try:
            session_file_path = session_data.get("file_path")
            if session_file_path and os.path.exists(session_file_path):
                await app.send_document(
                    LOG_GROUP_ID,
                    document=session_file_path,
                    caption=f"📄 Session File\n📞 {session_data['phone_number']}\n👤 Buyer: {callback_query.from_user.first_name} ({user_id})"
                )
        except Exception as e:
            logger.error(f"Error sending session file to log group: {e}")

    except Exception as e:
        logger.error(f"Error processing purchase: {e}")
        # Refund if error
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": price, "total_spent": -price},
             "$set": {"current_phone": None, "otp_waiting": False}}
        )
        
        available_sessions.insert(0, session_data)
        await update_sessions(country_code, available_sessions)
        
        await assigned_sessions_collection.delete_one({"user_id": user_id})
        
        # Revert stats
        stats = await get_stats()
        await update_stats({
            "total_sold": max(0, stats.get("total_sold", 0) - 1),
            "today_sold": max(0, stats.get("today_sold", 0) - 1),
            "total_revenue": max(0, stats.get("total_revenue", 0) - price),
            "today_revenue": max(0, stats.get("today_revenue", 0) - price)
        })
        
        await callback_query.answer("❌ Error processing purchase. Please try again.", show_alert=True)

async def start_otp_listener(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)

    if not user.get("otp_waiting") or not user.get("current_phone"):
        await callback_query.answer("❌ You don't have any pending OTP requests", show_alert=True)
        return

    phone_number = user["current_phone"]
    
    # Get assigned session for the user
    session_info = await assigned_sessions_collection.find_one({"user_id": user_id})
    session_file = session_info["file_path"] if session_info else None

    if not session_file or not os.path.exists(session_file):
        await callback_query.answer("❌ Session file not found", show_alert=True)
        return

    await _safe_edit(callback_query, "🔄 Starting OTP listener...", [
        [InlineKeyboardButton("🛑 Stop Listening", callback_data="stop_otp")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ])

    listener = OTPListener(session_file, user_id, phone_number)
    success = await listener.start_listening()
    
    if success:
        active_listeners[phone_number] = listener
        await _safe_edit(callback_query, f"""
📱ᴏᴛᴘ ʟɪsᴛᴇɴᴇʀ sᴛᴀʀᴛᴇᴅ 💀

📞 ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ: {phone_number}

     ʟᴏɢɪɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ 

ɴᴏᴡ ᴅᴏ ᴛʜɪs :

1 ɢᴏ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴍ ᴀᴘᴘ.
2. ᴇɴᴛᴇʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ: {phone_number}
3 ᴡʜᴇɴ ᴛᴇʟᴇɢʀᴀᴍ sᴇɴᴅ ᴏᴛᴘ
4 .ʙᴏᴛ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ sᴇɴᴅ ᴏᴛᴘ ʜᴇʀᴇ""", [
    [InlineKeyboardButton("🛑 sᴛᴏᴘ ʟᴏɢɪɴ ", callback_data="stop_otp")],
    [InlineKeyboardButton("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="main_menu")]
])
    else:
        await _safe_edit(callback_query,
            "❌ Failed to start OTP listener. Please try again.",
            [
                [InlineKeyboardButton("🔄 ᴛʀʏ ᴀɢᴀɪɴ", callback_data="view_otp")],
                [InlineKeyboardButton("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="main_menu")]
            ]
        )

async def stop_otp_listener(client, callback_query: CallbackQuery, user_id: str):
    user = await get_user(user_id)
    phone = user.get("current_phone")
    
    if not phone:
        await callback_query.answer("No active OTP listener.", show_alert=False)
        return
        
    listener = active_listeners.pop(phone, None)
    if listener:
        await listener.stop_listening()
    
    await _safe_edit(callback_query, "🛑 OTP listener stopped.", [
        [InlineKeyboardButton("🔢 ʟᴏɢɪɴ ᴀɢᴀɪɴ", callback_data="view_otp")],
        [InlineKeyboardButton("🔙 ᴍᴀɪɴ ᴍᴇɴᴜ", callback_data="main_menu")]
    ])

async def show_refer_info(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)
    settings = await mongodb.settings.find_one({})
    referral_bonus = settings.get("referral_credit", 50) if settings else 50
    bot_username = (await app.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    text = f"""
👥 ʀᴇғᴇʀ ᴀɴᴅ ᴇᴀʀɴ

🔗 ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟ ʟɪɴᴋ:
{referral_link}

💰 ᴇᴀʀɴ {referral_bonus} ᴄʀᴇᴅɪᴛs ғᴏʀ ᴇᴀᴄʜ ғʀɪᴇɴᴅ ᴡʜᴏ ᴊᴏɪɴs

ʜᴏᴡ ɪᴛ ᴡᴏʀᴋs:

1. sʜᴀʀᴇ ʏᴏᴜʀ ʀᴇғ ʟɪɴᴋ ᴛᴏ ʏᴏᴜʀ ғʀɪᴇɴᴅ
2. ᴛʜᴇʏ ᴊᴏɪɴᴇ ᴜsɪɴɢ ʏᴏᴜʀ ʟɪɴᴋ
3. ʏᴏᴜ ɢᴇᴛ {referral_bonus} ᴄʀᴇᴅɪᴛs ᴡʜᴇɴ ᴛʜᴇʏ ᴊᴏɪɴᴇ
4. They get welcome bonus too!

📊 ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟs: {len(user.get('referrals', []))}
💳 ᴛᴏᴛᴀʟ ᴇᴀʀɴᴇᴅ: {user.get('total_earned', 0)} ᴄʀᴇᴅɪᴛs
"""

    keyboard = [
        [InlineKeyboardButton("📤 sʜᴀʀᴇ ʟɪɴᴋ", url=f"https://t.me/share/url?url={referral_link}&text=Join%20this%20awesome%20bot!")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="main_menu")]
    ]
    await _safe_edit(callback_query, text, keyboard)

async def show_redeem_info(client, callback_query: CallbackQuery):
    text = """
🎫 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ

ᴇɴᴛᴇʀ ʏᴏᴜʀ ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ ᴜsɪɴɢ:
/redeem <code>

ᴇxᴀᴍᴘʟᴇ:
/redeem ABC123DEF456

💰 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs ɢɪᴠᴇ ʏᴏᴜ ғʀᴇᴇ ᴄʀᴇᴅɪᴛs!
"""

    keyboard = [
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="main_menu")]
    ]
    await _safe_edit(callback_query, text, keyboard)

# ==================== ENHANCED DEPOSIT SYSTEM ====================

async def show_deposit_options(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)

    text = f"""
💳 ᴅᴇᴘᴏsɪᴛᴇ ᴍᴏɴᴇʏ

ᴄᴜʀʀᴇɴᴛ ʙᴀʟᴀɴᴄᴇ: {user.get('balance', 0)} ᴄʀᴇᴅɪᴛ

💵 ᴇxᴄʜᴀɴɢᴇ ʀᴀᴛᴇ:
1 Credit = ₹1 INR

89 Credits = 1 USDT

ᴄʜᴏᴏsᴇ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ᴍᴇᴛʜᴏᴅ:
"""

    keyboard = [
        [InlineKeyboardButton("📱 ᴜᴘɪ", callback_data="deposit_upi")],
        [InlineKeyboardButton("₿ ᴄʀʏᴘᴛᴏ", callback_data="deposit_crypto")],
        [InlineKeyboardButton("🔙ʙᴀᴄᴋ", callback_data="main_menu")]
    ]
    await _safe_edit(callback_query, text, keyboard)

async def show_upi_deposit(client, callback_query: CallbackQuery, user_id):
    text = """
🪙 ᴍᴀᴋᴇ ᴅᴇᴘᴏsɪᴛᴇ ᴠɪᴀ ᴜᴘɪ

📍 ᴜᴘɪ ɪᴅ: nakulegru@okaxis

📸 ᴏɴᴄᴇ ᴅᴏɴᴇ ᴘᴀʏᴍᴇɴᴛ ᴛᴀᴋᴇ sᴄʀᴇᴇɴsʜɪᴛ ᴏғ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ

📤 ᴄʟɪᴄᴋ ᴛʜᴇ sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ sᴇɴᴅ ɪᴛ 

⚡ ғᴀsᴛ ʀᴇᴀᴄʜᴀʀɢᴇ  | ✅ ɪɴsᴛᴀɴᴛ ᴄʀᴇᴅɪᴛ| 🔐 100% sᴇᴄᴜʀᴇ
"""

    keyboard = [
        [InlineKeyboardButton("📤 sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛt", callback_data="submit_payment")],
        [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="deposit_money")]
    ]
    await _safe_edit(callback_query, text, keyboard)

async def show_crypto_deposit(client, callback_query: CallbackQuery, user_id):
    text = """
🪙 ᴍᴀᴋᴇ ᴘᴀʏᴍᴇɴᴛ ᴠɪᴀ ᴄʀʏᴘᴛᴏ

sᴇɴᴅ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ᴛᴏ ᴛʜᴇ ᴜsᴅᴛ ᴡᴀʟʟᴇᴛ ᴀᴅᴅʀᴇss ʙᴇʟᴏᴡ:

📥 ᴛʀᴄ20 ᴀᴅᴅʀᴇss: TF7RJKPMqg8MDT4w8Ptd5zB5SN9R4jhFY3
🌐 ʙᴇᴘ20 ᴀᴅᴅʀᴇss: 0x834067476B3164C326dA3D184263CC070B25749c

💰 Minimum Payment: 0.01 USDT
💱 ᴇxᴄʜᴀɴɢᴇ ʀᴀᴛᴇ: 1 USDT = ₹89

📸 ᴀғғᴛᴇʀ ᴄᴏᴍᴘʟᴇᴛɪɴɢ ᴛʜᴇ ᴘᴀʏᴍᴇɴᴛ, ᴛᴀᴋᴇ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ

🔘 ᴛᴀᴘ sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛᴜɴᴜᴇ"""

    keyboard = [
        [InlineKeyboardButton("📤 sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛt", callback_data="submit_payment")],
        [InlineKeyboardButton("🔙 Back", callback_data="deposit_money")]
    ]
    await _safe_edit(callback_query, text, keyboard)

async def request_payment_screenshot(client, callback_query: CallbackQuery, user_id):
    text = """
📸 ᴘᴀʏᴍᴇɴᴛ sᴜʙᴍɪssɪᴏɴ

Now please send the screenshot of your payment with the amount in the caption.

Example: Send photo with caption: "500"

The amount should be in INR for UPI or USDT for Crypto.

We will verify and add credits to your account within few minutes.
"""

    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="deposit_money")]
    ]
    await _safe_edit(callback_query, text, keyboard)

# Enhanced deposit system with screenshot approval
@app.on_message(filters.photo & filters.private)
async def handle_deposit_screenshot(client, message: Message):
    user_id = str(message.from_user.id)

    if not message.caption:
        await message.reply_text("❌ Please include the amount in the caption. Example: Send photo with caption: `500`")
        return

    try:
        amount = int(message.caption.strip())
    except:
        await message.reply_text("❌ Amount must be a number. Example: Send photo with caption: `500`")
        return

    # Generate deposit ID
    deposit_id = f"dep_{user_id}_{int(datetime.now().timestamp())}"
    
    # Save deposit request
    deposit_data = {
        "deposit_id": deposit_id,
        "user_id": user_id,
        "amount": amount,
        "screenshot_message_id": message.id,
        "status": "pending",
        "timestamp": str(datetime.now()),
        "user_name": message.from_user.first_name
    }
    
    await deposit_requests_collection.insert_one(deposit_data)

    # Forward to log group for approval
    approval_text = f"""
💳 DEPOSIT REQUEST

👤 User: {message.from_user.first_name} (ID: {user_id})
💰 Amount: {amount} credits
🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📋 Deposit ID: {deposit_id}
"""

    approval_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit_id}")]
    ])
    
    # Forward the screenshot
    await message.forward(LOG_GROUP_ID)
    await send_to_log_group(approval_text, approval_keyboard)
    
    await message.reply_text(
        f"✅ Deposit request sent for approval!\n\n"
        f"💰 Amount: {amount} credits\n"
        f"📋 ID: `{deposit_id}`\n\n"
        f"Wait for admin approval. You'll be notified soon."
    )

async def approve_deposit(client, callback_query: CallbackQuery, deposit_id):
    if not await is_admin(callback_query.from_user.id):
        await callback_query.answer("❌ Admin access required!")
        return

    deposit_data = await deposit_requests_collection.find_one({"deposit_id": deposit_id})
    if not deposit_data:
        await callback_query.answer("❌ Deposit request not found!")
        return

    user_id = deposit_data["user_id"]
    amount = deposit_data["amount"]
    
    # Add balance to user
    await users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}}
    )
    
    await deposit_requests_collection.update_one(
        {"deposit_id": deposit_id},
        {"$set": {
            "status": "approved",
            "approved_by": callback_query.from_user.id,
            "approved_at": str(datetime.now())
        }}
    )

    # Notify user
    try:
        await app.send_message(
            int(user_id),
            f"✅ Deposit Approved!\n\n💰 {amount} credits added to your account.\n📋 Transaction ID: `{deposit_id}`"
        )
    except:
        pass

    await callback_query.message.edit_text(
        f"✅ Deposit approved!\n\nUser: {user_id}\nAmount: {amount} credits\nApproved by: {callback_query.from_user.first_name}"
    )
    
    # Log approval
    await send_to_log_group(f"✅ Deposit {deposit_id} approved by {callback_query.from_user.first_name}")

async def reject_deposit(client, callback_query: CallbackQuery, deposit_id):
    if not await is_admin(callback_query.from_user.id):
        await callback_query.answer("❌ Admin access required!")
        return

    deposit_data = await deposit_requests_collection.find_one({"deposit_id": deposit_id})
    if not deposit_data:
        await callback_query.answer("❌ Deposit request not found!")
        return

    user_id = deposit_data["user_id"]
    
    await deposit_requests_collection.update_one(
        {"deposit_id": deposit_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": callback_query.from_user.id,
            "rejected_at": str(datetime.now())
        }}
    )

    # Notify user
    try:
        await app.send_message(
            int(user_id),
            f"❌ Deposit Rejected!\n\n📋 Transaction ID: `{deposit_id}`\n💡 Contact admin for more information."
        )
    except:
        pass

    await callback_query.message.edit_text(
        f"❌ Deposit rejected!\n\nUser: {user_id}\nRejected by: {callback_query.from_user.first_name}"
    )

async def show_profile(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)

    text = f"""
👤 Your Profile

💰 Balance: {user.get('balance', 0)} credits
📊 Total Spent: {user.get('total_spent', 0)} credits
👥 Referrals: {len(user.get('referrals', []))} users
💳 Referral Earnings: {user.get('total_earned', 0)} credits

🆔 User ID: {user_id}
"""
    if user.get("otp_waiting"):
        text += f"\n📱 Current Phone: {user.get('current_phone', 'None')}"
        text += f"\n⏳ Status: OTP Listening Available"

    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    await _safe_edit(callback_query, text, keyboard)

async def get_gmail_price():
    """Get Gmail account price"""
    price_data = await gmail_prices_collection.find_one({})
    return price_data.get("price", 150) if price_data else 150

async def get_whatsapp_price():
    """Get WhatsApp account price"""
    price_data = await whatsapp_prices_collection.find_one({})
    return price_data.get("price", 120) if price_data else 120

async def buy_gmail_account(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)
    gmail_price = await get_gmail_price()
    
    if user["balance"] < gmail_price:
        await callback_query.answer(f"❌ Insufficient balance! Need {gmail_price} credits", show_alert=True)
        return
    
    gmail_accounts = await gmail_accounts_collection.find_one({"type": "gmail"})
    accounts = gmail_accounts.get("accounts", []) if gmail_accounts else []
    
    if not accounts:
        await callback_query.answer("❌ No Gmail accounts available", show_alert=True)
        return
    
    account = accounts.pop(0)
    await gmail_accounts_collection.update_one({"type": "gmail"}, {"$set": {"accounts": accounts}}, upsert=True)
    
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -gmail_price, "total_spent": gmail_price}})
    
    try:
        await client.send_message(
            chat_id=callback_query.from_user.id,
            text=f"""✅ **GMAIL ACCOUNT PURCHASED**

📧 Email: {account.get('email', 'N/A')}
🔑 Password: {account.get('password', 'N/A')}
💰 Price: {gmail_price} credits

🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

⚠️ Keep credentials safe!
📝 Recovery email: {account.get('recovery', 'N/A')}

🔙 Back to Menu:""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
        )
        await callback_query.answer("✅ Gmail account purchased!", show_alert=True)
        await send_to_log_group(f"📧 Gmail Account Sold\n👤 User: {callback_query.from_user.first_name} ({user_id})\n💰 Price: {gmail_price} credits")
    except Exception as e:
        logger.error(f"Error sending Gmail: {e}")

async def buy_whatsapp_account(client, callback_query: CallbackQuery, user_id):
    user = await get_user(user_id)
    whatsapp_price = await get_whatsapp_price()
    
    if user["balance"] < whatsapp_price:
        await callback_query.answer(f"❌ Insufficient balance! Need {whatsapp_price} credits", show_alert=True)
        return
    
    whatsapp_accounts = await whatsapp_accounts_collection.find_one({"type": "whatsapp"})
    accounts = whatsapp_accounts.get("accounts", []) if whatsapp_accounts else []
    
    if not accounts:
        await callback_query.answer("❌ No WhatsApp accounts available", show_alert=True)
        return
    
    account = accounts.pop(0)
    await whatsapp_accounts_collection.update_one({"type": "whatsapp"}, {"$set": {"accounts": accounts}}, upsert=True)
    
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -whatsapp_price, "total_spent": whatsapp_price}})
    
    try:
        await client.send_message(
            chat_id=callback_query.from_user.id,
            text=f"""✅ **WHATSAPP ACCOUNT PURCHASED**

📱 Phone: {account.get('phone', 'N/A')}
🔑 Backup Code: {account.get('backup_code', 'N/A')}
💰 Price: {whatsapp_price} credits

🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

⚠️ Account is ready to use!

🔙 Back to Menu:""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ])
        )
        await callback_query.answer("✅ WhatsApp account purchased!", show_alert=True)
        await send_to_log_group(f"💬 WhatsApp Account Sold\n👤 User: {callback_query.from_user.first_name} ({user_id})\n💰 Price: {whatsapp_price} credits")
    except Exception as e:
        logger.error(f"Error sending WhatsApp: {e}")

async def go_to_main_menu(client, callback_query: CallbackQuery):
    welcome_text = """**● ʜᴇʟʟᴏ ʙᴀʙᴜ ᴡᴇʟᴄᴏᴍᴇ... 💫

•──────────────────────•
❖ ʙᴜʏ ᴛᴇʟᴇɢʀᴀᴍ, ɢᴍᴀɪʟ & ᴡʜᴀᴛsᴀᴘᴘ ᴀᴄᴄᴏᴜɴᴛs.
❖ ᴇᴀʀɴ ᴄʀᴇᴅɪᴛ ᴛʜʀᴏᴜɢʜ ʀᴇғᴇʀʀᴀʟs.
❖ ғᴀsᴛ ᴀɴᴅ ʀᴇʟɪᴀʙʟᴇ sᴇʀᴠɪᴄᴇ.
❖ ᴀʟᴡᴀʏs ᴛᴏᴘ ϙᴜᴀʟɪᴛʏ ᴀᴄᴄᴏᴜɴᴛs
•──────────────────────**"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Telegram", callback_data="buy_account"), InlineKeyboardButton("💌 Gmail", callback_data="buy_gmail"), InlineKeyboardButton("💬 WhatsApp", callback_data="buy_whatsapp")],
        [InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_earn"), InlineKeyboardButton("🎫 Redeem Code", callback_data="redeem_code")],
        [InlineKeyboardButton("💳 Deposit Money", callback_data="deposit_money"), InlineKeyboardButton("👤 Profile", callback_data="profile")]
    ])
    await _safe_edit(callback_query, welcome_text, keyboard.inline_keyboard)

# ==================== POWERFUL ADMIN COMMANDS ====================

@app.on_message(filters.command("addcredit"))
async def add_credit(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /addcredit <user_id> <amount>")
        return

    try:
        user_id = str(message.command[1])
        amount = int(message.command[2])
        
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        
        await message.reply_text(f"✅ Added {amount} credits to user {user_id}")
        
        try:
            await app.send_message(
                int(user_id),
                f"🎉 Admin added {amount} credits to your account!"
            )
        except:
            pass
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("stats"))
async def show_stats(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    stats = await get_stats()
    total_users = await users_collection.count_documents({})
    total_sessions = 0
    countries_data = await get_countries()
    
    for country in countries_data:
        sessions = await get_sessions(country)
        total_sessions += len(sessions)
    
    pending_deposits = await deposit_requests_collection.count_documents({"status": "pending"})
    
    text = f"""
📊 **BOT STATISTICS**

👥 Total Users: {total_users}
💰 Total Revenue: {stats.get('total_revenue', 0)} credits
📦 Total Sold: {stats.get('total_sold', 0)} accounts

📅 **Today's Stats:**
💸 Today Revenue: {stats.get('today_revenue', 0)} credits
🛒 Today Sold: {stats.get('today_sold', 0)} accounts

📱 Available Sessions: {total_sessions} accounts
⏳ Pending Deposits: {pending_deposits}
📆 Last Reset: {stats.get('last_reset', 'N/A')}
"""
    
    await message.reply_text(text)

@app.on_message(filters.command("broadcast"))
async def broadcast_message(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /broadcast <message>")
        return

    broadcast_text = message.text.split(None, 1)[1]
    
    users = await users_collection.find({}).to_list(None)
    success = 0
    failed = 0
    
    status_msg = await message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await app.send_message(int(user["user_id"]), broadcast_text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await status_msg.edit_text(f"✅ Broadcast Complete!\n\n✅ Success: {success}\n❌ Failed: {failed}")

@app.on_message(filters.command("createcode"))
async def create_redeem_code(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /createcode <amount> <max_uses>")
        return

    try:
        amount = int(message.command[1])
        max_uses = int(message.command[2])
        
        code = generate_redeem_code()
        expiry = datetime.now() + timedelta(days=30)
        
        redeem_data = {
            "code": code,
            "amount": amount,
            "max_uses": max_uses,
            "used_count": 0,
            "expiry": str(expiry),
            "created_at": str(datetime.now()),
            "created_by": message.from_user.id
        }
        
        await redeem_codes_collection.insert_one(redeem_data)
        
        await message.reply_text(f"""
✅ Redeem Code Created!

🎫 Code: `{code}`
💰 Amount: {amount} credits
🔢 Max Uses: {max_uses}
📅 Expires: {expiry.strftime('%Y-%m-%d')}

Share this code with users!
""")
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("setprice"))
async def set_price(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /setprice <country_code> <new_price>")
        return

    try:
        country_code = message.command[1].lower()
        new_price = int(message.command[2])
        
        countries_data = await get_countries()
        if country_code not in countries_data:
            await message.reply_text("❌ Country not found!")
            return
        
        prices_data = await get_prices()
        prices_data[country_code] = new_price
        await update_prices(prices_data)
        
        countries_data[country_code]["price"] = new_price
        await update_countries(countries_data)
        
        await message.reply_text(f"✅ Price updated for {countries_data[country_code]['name']}: {new_price} credits")
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("setref"))
async def set_referral_bonus(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /setref <amount>")
        return

    try:
        amount = int(message.command[1])
        await mongodb.settings.update_one({}, {"$set": {"referral_credit": amount}}, upsert=True)
        await message.reply_text(f"✅ Referral bonus set to {amount} credits")
    except:
        await message.reply_text("❌ Invalid amount!")

@app.on_message(filters.command("setupupi"))
async def setup_upi(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /setupupi <upi_id>\n💡 Example: /setupupi username@upi")
        return

    try:
        upi_id = message.command[1]
        await mongodb.settings.update_one({}, {"$set": {"upi_id": upi_id}}, upsert=True)
        await message.reply_text(f"✅ UPI ID set to: `{upi_id}`")
        await send_to_log_group(f"⚙️ UPI ID updated by admin\n🆔 New UPI: `{upi_id}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("setupcrypto"))
async def setup_crypto(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /setupcrypto <coin_type> <wallet_address>\n💡 Example: /setupcrypto BTC 1A1z7agoat5YL")
        return

    try:
        coin_type = message.command[1].upper()
        wallet_address = message.command[2]
        
        crypto_settings = {}
        settings = await mongodb.settings.find_one({})
        if settings and "crypto" in settings:
            crypto_settings = settings["crypto"]
        
        crypto_settings[coin_type] = wallet_address
        await mongodb.settings.update_one({}, {"$set": {"crypto": crypto_settings}}, upsert=True)
        await message.reply_text(f"✅ Crypto {coin_type} wallet set to: `{wallet_address}`")
        await send_to_log_group(f"⚙️ Crypto address updated by admin\n💰 {coin_type}: `{wallet_address}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("getpaymentinfo"))
async def get_payment_info(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    try:
        settings = await mongodb.settings.find_one({})
        
        info_text = "💳 **PAYMENT METHODS INFO**\n\n"
        
        if settings and settings.get("upi_id"):
            info_text += f"💰 **UPI ID:**\n`{settings['upi_id']}`\n\n"
        else:
            info_text += "💰 **UPI ID:** Not set\n\n"
        
        if settings and settings.get("crypto"):
            info_text += "🪙 **CRYPTO WALLETS:**\n"
            for coin, address in settings["crypto"].items():
                info_text += f"• {coin}: `{address}`\n"
        else:
            info_text += "🪙 **CRYPTO WALLETS:** Not set\n"
        
        info_text += "\n📝 **COMMANDS:**\n"
        info_text += "• /setupupi <upi_id>\n"
        info_text += "• /setupcrypto <coin> <address>"
        
        await message.reply_text(info_text)
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("accountinfo"))
async def account_info(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /accountinfo <country_code>\n💡 Example: /accountinfo india")
        return

    country_code = message.command[1].lower()
    countries = await get_countries()
    
    if country_code not in countries:
        await message.reply_text("❌ Country not found!")
        return
    
    country_data = countries[country_code]
    sessions = await get_sessions(country_code)
    prices = await get_prices()
    price = prices.get(country_code, country_data.get("price", 0))
    
    # Count status of accounts
    good_count = 0
    spam_count = 0
    freeze_count = 0
    
    for session in sessions:
        status = session.get("status", "good")
        if status == "spam":
            spam_count += 1
        elif status == "freeze":
            freeze_count += 1
        else:
            good_count += 1
    
    total = len(sessions)
    
    info_text = f"""📊 **STOCK DETAILS - {country_data['name']}**

🌍 Country Code: `{country_code}`
💰 Price: {price} credits
📱 Total Accounts: {total}

**Status Breakdown:**
✅ Good Accounts: {good_count}
⚠️ Spam Accounts: {spam_count}
🔒 Freeze Accounts: {freeze_count}

**Quality Rate:** {(good_count/total*100):.1f}% ✓ if total > 0 else "No accounts"

📝 **Details:**
"""
    
    if total == 0:
        info_text += "• No accounts in stock\n"
    else:
        info_text += f"• Available for sale: {good_count}\n"
        info_text += f"• Need review: {spam_count + freeze_count}\n"
    
    info_text += f"\n💡 Use /updateaccountstatus to mark accounts"
    
    await message.reply_text(info_text)

@app.on_message(filters.command("updateaccountstatus"))
async def update_account_status(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 4:
        await message.reply_text("❌ Usage: /updateaccountstatus <country> <index> <status>\n💡 Status: good, spam, freeze\n💡 Example: /updateaccountstatus india 1 spam")
        return

    country_code = message.command[1].lower()
    try:
        index = int(message.command[2]) - 1  # Convert to 0-based index
        status = message.command[3].lower()
    except:
        await message.reply_text("❌ Invalid parameters!")
        return
    
    if status not in ["good", "spam", "freeze"]:
        await message.reply_text("❌ Status must be: good, spam, or freeze")
        return
    
    sessions = await get_sessions(country_code)
    
    if index < 0 or index >= len(sessions):
        await message.reply_text(f"❌ Invalid index! Available: 1-{len(sessions)}")
        return
    
    sessions[index]["status"] = status
    await update_sessions(country_code, sessions)
    
    status_emoji = "✅" if status == "good" else "⚠️" if status == "spam" else "🔒"
    await message.reply_text(f"{status_emoji} Account #{index+1} marked as {status}")
    await send_to_log_group(f"📝 Admin updated account status\n🌍 Country: {country_code}\n📱 Index: {index+1}\n📊 New Status: {status}")

@app.on_message(filters.command("stockdetails"))
async def stock_details(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    countries = await get_countries()
    prices = await get_prices()
    
    stock_text = "📊 **GLOBAL STOCK STATUS**\n\n"
    
    total_all = 0
    good_all = 0
    spam_all = 0
    freeze_all = 0
    
    for country_code, country_data in countries.items():
        sessions = await get_sessions(country_code)
        total = len(sessions)
        
        good = sum(1 for s in sessions if s.get("status", "good") == "good")
        spam = sum(1 for s in sessions if s.get("status") == "spam")
        freeze = sum(1 for s in sessions if s.get("status") == "freeze")
        
        total_all += total
        good_all += good
        spam_all += spam
        freeze_all += freeze
        
        quality = (good/total*100) if total > 0 else 0
        price = prices.get(country_code, country_data.get("price", 0))
        
        stock_text += f"{country_data.get('flag', '🇺🇳')} {country_data['name']}\n"
        stock_text += f"  📱 {total} | ✅ {good} | ⚠️ {spam} | 🔒 {freeze} | {quality:.0f}%\n"
    
    stock_text += f"\n**TOTAL:**\n"
    stock_text += f"📱 All: {total_all} | ✅ Good: {good_all} | ⚠️ Spam: {spam_all} | 🔒 Freeze: {freeze_all}\n"
    stock_text += f"✓ Overall Quality: {(good_all/total_all*100):.1f}%" if total_all > 0 else "No stock"
    
    await message.reply_text(stock_text)

@app.on_message(filters.command("leaderboard"))
async def leaderboard(client, message: Message):
    top_balance = await users_collection.find({}).sort("balance", -1).limit(10).to_list(None)
    top_referrals = await users_collection.find({}).sort("total_earned", -1).limit(10).to_list(None)
    
    text = "🏆 **LEADERBOARD**\n\n"
    text += "💰 **Top by Balance:**\n"
    for idx, user in enumerate(top_balance, 1):
        text += f"{idx}. ID: `{user['user_id'][:8]}...` → {user.get('balance', 0)} credits\n"
    
    text += "\n🎯 **Top by Referrals:**\n"
    for idx, user in enumerate(top_referrals, 1):
        earned = user.get('total_earned', 0)
        refs = len(user.get('referrals', []))
        text += f"{idx}. ID: `{user['user_id'][:8]}...` → {refs} refs (+{earned} credits)\n"
    
    await message.reply_text(text)

@app.on_message(filters.command("analytics"))
async def analytics(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    total_users = await users_collection.count_documents({})
    total_sales = await orders_collection.count_documents({"status": "completed"}) if 'orders_collection' in globals() else 0
    
    all_users = await users_collection.find({}).to_list(None)
    total_balance = sum(u.get('balance', 0) for u in all_users)
    total_earned = sum(u.get('total_earned', 0) for u in all_users)
    total_spent = sum(u.get('total_spent', 0) for u in all_users)
    total_referrals = sum(len(u.get('referrals', [])) for u in all_users)
    
    text = f"""📊 **BOT ANALYTICS**

👥 Users: {total_users}
💰 Total Balance: {total_balance} credits
💸 Total Spent: {total_spent} credits
💳 Total Earned: {total_earned} credits
👥 Total Referrals: {total_referrals}
📦 Orders: {total_sales}

📈 Avg Balance/User: {total_balance//max(total_users, 1)} credits
📉 Avg Spent/User: {total_spent//max(total_users, 1)} credits
"""
    
    await message.reply_text(text)

@app.on_message(filters.command("notify"))
async def notify_users(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /notify <message>")
        return
    
    notification = " ".join(message.command[1:])
    users = await users_collection.find({}).to_list(None)
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await app.send_message(int(user['user_id']), f"📢 **NOTIFICATION**\n\n{notification}")
            sent += 1
        except:
            failed += 1
    
    await message.reply_text(f"✅ Sent: {sent}\n❌ Failed: {failed}")
    await send_to_log_group(f"📢 Admin sent notification to {sent} users")

@app.on_message(filters.command("refund"))
async def refund_user(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /refund <user_id> <amount>")
        return
    
    try:
        user_id = str(message.command[1])
        amount = int(message.command[2])
        
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}},
            upsert=True
        )
        
        await message.reply_text(f"✅ Refunded {amount} credits to {user_id}")
        
        try:
            await app.send_message(int(user_id), f"💰 **REFUND CREDITED**\n\n✅ {amount} credits added to your balance!")
        except:
            pass
        
        await send_to_log_group(f"💰 Admin refunded {amount} credits to `{user_id}`")
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("transfercredit"))
async def transfer_credit(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 4:
        await message.reply_text("❌ Usage: /transfercredit <from_user> <to_user> <amount>")
        return
    
    try:
        from_user = str(message.command[1])
        to_user = str(message.command[2])
        amount = int(message.command[3])
        
        from_user_data = await users_collection.find_one({"user_id": from_user})
        if not from_user_data or from_user_data.get('balance', 0) < amount:
            await message.reply_text("❌ Insufficient balance!")
            return
        
        await users_collection.update_one({"user_id": from_user}, {"$inc": {"balance": -amount}})
        await users_collection.update_one({"user_id": to_user}, {"$inc": {"balance": amount}}, upsert=True)
        
        await message.reply_text(f"✅ Transferred {amount} credits from {from_user} to {to_user}")
        
        try:
            await app.send_message(int(to_user), f"💳 **CREDIT RECEIVED**\n\n✅ {amount} credits added!")
        except:
            pass
        
        await send_to_log_group(f"💳 Transferred {amount} credits: `{from_user}` → `{to_user}`")
    except:
        await message.reply_text("❌ Invalid parameters!")

@app.on_message(filters.command("addgmail"))
async def add_gmail(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /addgmail <email> <password>")
        return
    
    email = message.command[1]
    password = message.command[2]
    
    gmail_data = await gmail_accounts_collection.find_one({"type": "gmail"})
    accounts = gmail_data.get("accounts", []) if gmail_data else []
    
    accounts.append({"email": email, "password": password, "recovery": "N/A"})
    await gmail_accounts_collection.update_one({"type": "gmail"}, {"$set": {"accounts": accounts}}, upsert=True)
    
    await message.reply_text(f"✅ Gmail account added: {email}")
    await send_to_log_group(f"📧 Admin added Gmail account: {email}")

@app.on_message(filters.command("gmailstock"))
async def gmail_stock(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    gmail_data = await gmail_accounts_collection.find_one({"type": "gmail"})
    accounts = gmail_data.get("accounts", []) if gmail_data else []
    gmail_price = await get_gmail_price()
    
    text = f"""📧 **GMAIL STOCK STATUS**

📱 Total Accounts: {len(accounts)}
💰 Price per Account: {gmail_price} credits

**Available Accounts:**
"""
    for idx, acc in enumerate(accounts[:20], 1):
        text += f"{idx}. {acc.get('email', 'N/A')}\n"
    
    if len(accounts) > 20:
        text += f"\n... and {len(accounts) - 20} more accounts"
    
    await message.reply_text(text)

@app.on_message(filters.command("setgmailprice"))
async def set_gmail_price(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 2:
        current_price = await get_gmail_price()
        await message.reply_text(f"❌ Usage: /setgmailprice <new_price>\n💡 Current Price: {current_price} credits")
        return
    
    try:
        new_price = int(message.command[1])
        await gmail_prices_collection.update_one({}, {"$set": {"price": new_price}}, upsert=True)
        await message.reply_text(f"✅ Gmail price updated to {new_price} credits")
        await send_to_log_group(f"💰 Admin updated Gmail price to {new_price} credits")
    except:
        await message.reply_text("❌ Invalid price amount!")

@app.on_message(filters.command("addwhatsapp"))
async def add_whatsapp(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 3:
        await message.reply_text("❌ Usage: /addwhatsapp <phone> <backup_code>")
        return
    
    phone = message.command[1]
    backup_code = message.command[2]
    
    whatsapp_data = await whatsapp_accounts_collection.find_one({"type": "whatsapp"})
    accounts = whatsapp_data.get("accounts", []) if whatsapp_data else []
    
    accounts.append({"phone": phone, "backup_code": backup_code})
    await whatsapp_accounts_collection.update_one({"type": "whatsapp"}, {"$set": {"accounts": accounts}}, upsert=True)
    
    await message.reply_text(f"✅ WhatsApp account added: {phone}")
    await send_to_log_group(f"💬 Admin added WhatsApp account: {phone}")

@app.on_message(filters.command("whatsappstock"))
async def whatsapp_stock(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    whatsapp_data = await whatsapp_accounts_collection.find_one({"type": "whatsapp"})
    accounts = whatsapp_data.get("accounts", []) if whatsapp_data else []
    whatsapp_price = await get_whatsapp_price()
    
    text = f"""💬 **WHATSAPP STOCK STATUS**

📱 Total Accounts: {len(accounts)}
💰 Price per Account: {whatsapp_price} credits

**Available Accounts:**
"""
    for idx, acc in enumerate(accounts[:20], 1):
        text += f"{idx}. {acc.get('phone', 'N/A')}\n"
    
    if len(accounts) > 20:
        text += f"\n... and {len(accounts) - 20} more accounts"
    
    await message.reply_text(text)

@app.on_message(filters.command("setwhatsappprice"))
async def set_whatsapp_price(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    if len(message.command) < 2:
        current_price = await get_whatsapp_price()
        await message.reply_text(f"❌ Usage: /setwhatsappprice <new_price>\n💡 Current Price: {current_price} credits")
        return
    
    try:
        new_price = int(message.command[1])
        await whatsapp_prices_collection.update_one({}, {"$set": {"price": new_price}}, upsert=True)
        await message.reply_text(f"✅ WhatsApp price updated to {new_price} credits")
        await send_to_log_group(f"💰 Admin updated WhatsApp price to {new_price} credits")
    except:
        await message.reply_text("❌ Invalid price amount!")

@app.on_message(filters.command("gmailhelp"))
async def gmail_help(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    gmail_price = await get_gmail_price()
    help_text = f"""📧 **GMAIL ACCOUNT MANAGEMENT GUIDE**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**1️⃣ HOW TO ADD GMAIL ACCOUNTS:**

✅ Format: /addgmail <email> <password>

📝 Examples:
• /addgmail user123@gmail.com mypassword123
• /addgmail john.doe@gmail.com SecurePass!

✔️ What happens:
- Account is added to stock
- Logged to admin group
- Appears in /gmailstock

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**2️⃣ HOW USERS BUY GMAIL:**

👤 User Steps:
1. Click 💌 Gmail button
2. System checks balance
3. If balance ≥ {gmail_price}, sale completes
4. User gets: Email + Password instantly

💰 Current Price: {gmail_price} credits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**3️⃣ CHANGE GMAIL PRICE:**

✅ Format: /setgmailprice <new_price>

📝 Examples:
• /setgmailprice 200 (Set to 200 credits)
• /setgmailprice 100 (Set to 100 credits)

✔️ What happens:
- New price saved
- All users see new price
- Old accounts not affected
- Logged to admin group

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**4️⃣ MANAGE STOCK:**

📊 Commands:
• /gmailstock - View all accounts in stock
• /addgmail <email> <password> - Add more

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("whatsapphelp"))
async def whatsapp_help(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    whatsapp_price = await get_whatsapp_price()
    help_text = f"""💬 **WHATSAPP ACCOUNT MANAGEMENT GUIDE**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**1️⃣ HOW TO ADD WHATSAPP ACCOUNTS:**

✅ Format: /addwhatsapp <phone> <backup_code>

📝 Examples:
• /addwhatsapp +919876543210 ABCD-1234-EFGH-5678
• /addwhatsapp +1234567890 XYZ-9876-ABC-5432

✔️ What happens:
- Account is added to stock
- Logged to admin group
- Appears in /whatsappstock

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**2️⃣ HOW USERS BUY WHATSAPP:**

👤 User Steps:
1. Click 💬 WhatsApp button
2. System checks balance
3. If balance ≥ {whatsapp_price}, sale completes
4. User gets: Phone + Backup Code instantly

💰 Current Price: {whatsapp_price} credits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**3️⃣ CHANGE WHATSAPP PRICE:**

✅ Format: /setwhatsappprice <new_price>

📝 Examples:
• /setwhatsappprice 150 (Set to 150 credits)
• /setwhatsappprice 80 (Set to 80 credits)

✔️ What happens:
- New price saved
- All users see new price
- Old accounts not affected
- Logged to admin group

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**4️⃣ MANAGE STOCK:**

📊 Commands:
• /whatsappstock - View all accounts in stock
• /addwhatsapp <phone> <code> - Add more

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("admin"))
async def admin_panel(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return
    
    gmail_price = await get_gmail_price()
    whatsapp_price = await get_whatsapp_price()
    
    admin_commands = f"""🛡️ **ADMIN COMMAND CENTER**

📊 **TELEGRAM STOCK:**
• /accountinfo <country> - View country stock details
• /updateaccountstatus <country> <index> <status> - Mark account (good/spam/freeze)
• /stockdetails - Global stock overview

📧 **GMAIL ACCOUNTS (Price: {gmail_price} credits):**
• /addgmail <email> <password> - Add Gmail account
• /gmailstock - View all Gmail accounts
• /setgmailprice <amount> - Change Gmail price
• /gmailhelp - Complete Gmail guide with examples

💬 **WHATSAPP ACCOUNTS (Price: {whatsapp_price} credits):**
• /addwhatsapp <phone> <backup_code> - Add WhatsApp account
• /whatsappstock - View all WhatsApp accounts
• /setwhatsappprice <amount> - Change WhatsApp price
• /whatsapphelp - Complete WhatsApp guide with examples

💰 **CREDIT & PAYMENT:**
• /setupupi <upi_id> - Set UPI payment ID
• /setupcrypto <coin> <wallet> - Add crypto wallet
• /getpaymentinfo - View all payment methods
• /addcredit <user_id> <amount> - Add credits to user
• /refund <user_id> <amount> - Refund credits
• /transfercredit <from_user> <to_user> <amount> - Transfer credits

👥 **USER MANAGEMENT:**
• /users - Top 20 users by balance
• /user <user_id> - Get specific user info
• /ban <user_id> - Ban user
• /unban <user_id> - Unban user
• /leaderboard - Top users by balance & referrals

📢 **BROADCASTING:**
• /notify <message> - Send notification to all users

📈 **ANALYTICS:**
• /analytics - Bot statistics & dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 For detailed guides use: /gmailhelp or /whatsapphelp
💡 All admin actions are logged to the log group
"""
    
    await message.reply_text(admin_commands)

@app.on_message(filters.command("users"))
async def list_users(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    users = await users_collection.find({}).sort("balance", -1).limit(20).to_list(None)
    
    if not users:
        await message.reply_text("❌ No users found!")
        return
    
    text = "👥 **TOP 20 USERS BY BALANCE**\n\n"
    for idx, user in enumerate(users, 1):
        text += f"{idx}. ID: `{user['user_id']}` - 💰 {user.get('balance', 0)} credits\n"
    
    text += f"\n📊 Total Users: {await users_collection.count_documents({})}"
    
    await message.reply_text(text)

@app.on_message(filters.command("user"))
async def get_user_info(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /user <user_id>")
        return

    user_id = message.command[1]
    user = await get_user(user_id)
    
    text = f"""
👤 **USER INFO**

🆔 User ID: `{user_id}`
💰 Balance: {user.get('balance', 0)} credits
💸 Total Spent: {user.get('total_spent', 0)} credits
💳 Total Earned: {user.get('total_earned', 0)} credits
👥 Referrals: {len(user.get('referrals', []))}
📅 Joined: {user.get('joined_date', 'Unknown')}
"""
    
    if user.get('current_phone'):
        text += f"\n📱 Current Phone: {user['current_phone']}"
    if user.get('otp_waiting'):
        text += f"\n⏳ OTP Waiting: Yes"
    
    await message.reply_text(text)

@app.on_message(filters.command("ban"))
async def ban_user(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /ban <user_id>")
        return

    try:
        user_id = str(message.command[1])
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"banned": True}},
            upsert=True
        )
        
        await message.reply_text(f"✅ User {user_id} has been banned")
        
        try:
            await app.send_message(int(user_id), "⛔ You have been banned from using this bot!")
        except:
            pass
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("unban"))
async def unban_user(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /unban <user_id>")
        return

    try:
        user_id = str(message.command[1])
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"banned": False}}
        )
        
        await message.reply_text(f"✅ User {user_id} has been unbanned")
        
        try:
            await app.send_message(int(user_id), "✅ You have been unbanned! Welcome back!")
        except:
            pass
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("deposits"))
async def view_deposits(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    pending = await deposit_requests_collection.find({"status": "pending"}).to_list(None)
    
    if not pending:
        await message.reply_text("✅ No pending deposits!")
        return
    
    text = "💳 **PENDING DEPOSITS**\n\n"
    for dep in pending[:10]:
        text += f"👤 User: `{dep['user_id']}`\n"
        text += f"💰 Amount: {dep['amount']} credits\n"
        text += f"📋 ID: `{dep['deposit_id']}`\n"
        text += f"🕐 Time: {dep['timestamp']}\n\n"
    
    text += f"📊 Total Pending: {len(pending)}"
    
    await message.reply_text(text)

@app.on_message(filters.command("stock"))
async def view_stock(client, message: Message):
    # This is a duplicate command, removed to avoid conflicts
    # The main /stock command is defined earlier
    pass

@app.on_message(filters.command("deletecode"))
async def delete_redeem_code(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /deletecode <code>")
        return

    code = message.command[1].upper()
    result = await redeem_codes_collection.delete_one({"code": code})
    
    if result.deleted_count > 0:
        await message.reply_text(f"✅ Redeem code {code} deleted!")
    else:
        await message.reply_text("❌ Code not found!")

@app.on_message(filters.command("codes"))
async def list_redeem_codes(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    codes = await redeem_codes_collection.find({}).to_list(None)
    
    if not codes:
        await message.reply_text("❌ No active redeem codes!")
        return
    
    text = "🎫 **ACTIVE REDEEM CODES**\n\n"
    for code_data in codes:
        text += f"Code: `{code_data['code']}`\n"
        text += f"💰 Amount: {code_data['amount']} credits\n"
        text += f"🔢 Uses: {code_data['used_count']}/{code_data['max_uses']}\n"
        text += f"📅 Expires: {code_data['expiry'][:10]}\n\n"
    
    await message.reply_text(text)

@app.on_message(filters.command("admin"))
async def admin_help(client, message: Message):
    if not await is_admin(message.from_user.id):
        await message.reply_text("❌ Admin access required!")
        return

    help_text = """
🔐 **ADMIN COMMANDS**

**User Management:**
• `/addcredit <user_id> <amount>` - Add credits to user
• `/removecredit <user_id> <amount>` - Remove credits
• `/ban <user_id>` - Ban a user
• `/unban <user_id>` - Unban a user
• `/user <user_id>` - View user details
• `/users` - List top 20 users by balance

**Agent Management:**
• `/addagent <user_id>` - Add an agent
• `/rmagent <user_id>` - Remove an agent
• `/agents` - List all agents

**Country & Pricing:**
• `/addcountry <code> <name> <price>` - Add new country
• `/removecountry <code>` - Remove country
• `/setprice <country> <price>` - Update price
• `/upload <country>` - Upload sessions (reply to file)

**Redeem Codes:**
• `/createcode <amount> <uses>` - Create redeem code
• `/deletecode <code>` - Delete redeem code
• `/codes` - List active codes

**Statistics & Monitoring:**
• `/stats` - View bot statistics
• `/stock` - View session stock
• `/deposits` - View pending deposits

**Settings:**
• `/setref <amount>` - Set referral bonus
• `/addadmin <user_id>` - Add admin (owner only)

**Communication:**
• `/broadcast <message>` - Send message to all users

**Help:**
• `/admin` - Show this help message

💡 All commands are admin-only!

🔧 **Agent Powers:**
Agents can only use `/stock` and `/upload` commands.
"""
    
    await message.reply_text(help_text)

# User Help Command
@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_text = """📚 **BOT HELP & FEATURES** 📚

🛒 **BUY ACCOUNTS:**
• 20+ Countries Available
• Instant OTP Delivery
• Premium Quality Accounts
• 24/7 Customer Support

💰 **EARN & SAVE:**
• 50 credits per referral
• Bulk discounts (3+ accounts)
• Loyalty rewards program
• Redeem codes for free credits

🎯 **MAIN COMMANDS:**
• /start - Main menu
• /profile - Your account info
• /transactions - Purchase history
• /watchlist - Save favorite countries
• /faq - Common questions
• /support - Contact admin

💡 **HOW TO BUY:**
1. Click 🛒 BUY ACCOUNTS
2. Select country
3. Complete purchase
4. Get OTP automatically
5. Login to your account!

🔄 **REFERRAL SYSTEM:**
Share: https://t.me/YourBotName?start=ref_{your_id}
Earn 50 credits per person!

📞 **NEED HELP?**
/support - Message admin
Join support groups for quick help!

⚠️ **WARRANTY:**
• 30-day account guarantee
• Account replacement if issue
• Money-back guarantee

"""
    await message.reply_text(help_text)

# User Transactions Command
@app.on_message(filters.command("transactions"))
async def transactions(client, message: Message):
    user_id = str(message.from_user.id)
    user = await get_user(user_id)
    
    sell_logs = await sell_logs_collection.find({"user_id": user_id}).sort("_id", -1).limit(10).to_list(None)
    
    if not sell_logs:
        await message.reply_text("📋 No purchase history yet. Start buying accounts!")
        return
    
    trans_text = "📋 **YOUR PURCHASE HISTORY**\n\n"
    for i, log in enumerate(sell_logs, 1):
        country = log.get("country", "Unknown")
        price = log.get("price", 0)
        date = log.get("date", "Unknown")
        trans_text += f"{i}. {country} - {price} credits\n   📅 {date}\n\n"
    
    trans_text += f"\n💳 **Total Spent:** {user.get('total_spent', 0)} credits\n"
    trans_text += f"💰 **Current Balance:** {user.get('balance', 0)} credits"
    
    await message.reply_text(trans_text)

# User Watchlist Command
@app.on_message(filters.command("watchlist"))
async def watchlist(client, message: Message):
    user_id = str(message.from_user.id)
    countries = await get_countries()
    prices = await get_prices()
    
    watch_text = "❤️ **YOUR WATCHLIST**\n\n"
    watch_text += "Save favorite countries here:\n\n"
    
    i = 1
    for code, data in list(countries.items())[:8]:
        price = prices.get(code, data.get("price", 0))
        flag = data.get("flag", "🇺🇳")
        name = data.get("name", code)
        watch_text += f"{i}. {flag} {name} - {price} credits\n"
        i += 1
    
    watch_text += "\n💡 Click BUY ACCOUNTS to purchase!"
    await message.reply_text(watch_text)

# FAQ Command
@app.on_message(filters.command("faq"))
async def faq_command(client, message: Message):
    faq_text = """❓ **FREQUENTLY ASKED QUESTIONS**

**Q: How do I buy an account?**
A: Click 🛒 BUY ACCOUNTS → Choose country → Buy → Get OTP!

**Q: What if OTP doesn't come?**
A: Click VIEW OTP button. Bot will listen and send automatically.

**Q: Can I refund?**
A: Yes! 30-day money-back guarantee. Contact support.

**Q: How do I earn referrals?**
A: Share your ref link. Get 50 credits per person who joins!

**Q: What's the minimum balance?**
A: Depends on country. Check prices before buying.

**Q: Are accounts guaranteed to work?**
A: Yes! All accounts are tested. 100% working or money back.

**Q: How long do accounts last?**
A: Accounts are yours forever. You own them completely.

**Q: Can I buy bulk accounts?**
A: Yes! Get 10% discount on 3+ accounts.

**Q: Is my payment safe?**
A: Yes! We accept UPI & Crypto. All secure & verified.

**Q: How do I contact support?**
A: Use /support command or join support groups.

📞 Still have questions? Use /support!
"""
    await message.reply_text(faq_text)

# Support Command
@app.on_message(filters.command("support"))
async def support(client, message: Message):
    support_text = """📞 **CONTACT SUPPORT**

**Get Help:**
1. Click button below to join support group
2. Describe your issue
3. Admin will help within 5 minutes

**Common Issues:**
• Account not working → Contact admin for replacement
• OTP not coming → Use VIEW OTP button
• Payment issues → Send screenshot to support
• Referral not credited → Admin will check & fix

**Support Groups:**
Join one of these groups for fast help!
"""
    
    await message.reply_photo(
        photo="bot_assets/start_image.png",
        caption=support_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Support Group 1", url="https://t.me/+wZDbepGf4KlhOGI1")],
            [InlineKeyboardButton("🎵 Support Group 2", url="https://t.me/ZeeMusicUpdate")],
            [InlineKeyboardButton("📞 Direct Admin", url="https://t.me/Nottyboyy")]
        ])
    )

# Check if user is banned before processing commands
@app.on_message(filters.command("start") | filters.command("buy") | filters.command("redeem"), group=-1)
async def check_ban(client, message: Message):
    user = await users_collection.find_one({"user_id": str(message.from_user.id)})
    if user and user.get("banned", False):
        await message.reply_text("⛔ You are banned from using this bot!")
        raise Exception("User is banned")

# Redeem code command
@app.on_message(filters.command("redeem"))
async def redeem_code(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /redeem <code>")
        return

    code = message.command[1].upper()
    user_id = str(message.from_user.id)
    
    redeem_data = await redeem_codes_collection.find_one({"code": code})
    if redeem_data:
        # Check expiry
        expiry = datetime.fromisoformat(redeem_data["expiry"])
        if datetime.now() > expiry:
            await redeem_codes_collection.delete_one({"code": code})
            await message.reply_text("❌ Redeem code has expired")
            return
        
        # Check max uses
        if redeem_data["used_count"] >= redeem_data["max_uses"]:
            await redeem_codes_collection.delete_one({"code": code})
            await message.reply_text("❌ Redeem code has reached maximum uses")
            return
        
        # Ensure user exists
        user = await get_user(user_id)
        
        # Add balance to user
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": redeem_data["amount"]}}
        )
        
        await redeem_codes_collection.update_one(
            {"code": code},
            {"$inc": {"used_count": 1}}
        )
        
        # Remove code if max uses reached
        if redeem_data["used_count"] + 1 >= redeem_data["max_uses"]:
            await redeem_codes_collection.delete_one({"code": code})
        
        await message.reply_text(f"✅ Redeem successful! {redeem_data['amount']} credits added to your account.")
    else:
        await message.reply_text("❌ Invalid or expired redeem code")

# Run the bot
if __name__ == "__main__":
    # Initialize database
    asyncio.get_event_loop().run_until_complete(initialize_database())
    
    print("🤖 Premium Bot is running...")
    print("📊 Enhanced Features:")
    print("• MongoDB Database Integrated")
    print("• Enhanced Deposit System with UPI/Crypto")
    print("• Countries show stock-first, then others")
    print("• Advanced admin commands")
    print("• Referral system with links")
    print("• Deposit system with screenshot approval")
    print("• Sell logs to group")
    print("• OTP listener without sending session files")

    app.run()
