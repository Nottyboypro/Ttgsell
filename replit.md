# Telegram Session Bot

## Overview
This is a Telegram bot that manages and sells Telegram session accounts with automatic OTP listening functionality. The bot allows users to purchase accounts from various countries, receive phone numbers, and automatically get OTP codes for login.

## Project Type
- **Type**: Telegram Bot (Python)
- **Framework**: Pyrogram + Telethon
- **Database**: MongoDB (Motor async driver)
- **Runtime**: Python 3.11

## Key Features
- **Account Sales**: Sell Telegram session accounts by country
- **OTP Listening**: Automatic OTP code retrieval using Telethon
- **User Management**: Balance, referral system, and profile tracking
- **Admin Panel**: Country management, pricing, user credits, deposit approvals
- **Payment System**: UPI and Crypto deposit options with screenshot verification
- **Referral System**: Earn credits by referring new users
- **Redeem Codes**: Admin-generated codes for free credits

## Project Structure
```
.
├── bot.py              # Main bot application
├── requirements.txt    # Python dependencies
├── sessions/          # Telegram session files (auto-created)
├── temp/              # Temporary files (auto-created)
├── bot_assets/        # Start image and assets
├── Procfile           # Heroku deployment config (optional)
├── runtime.txt        # Python version specification
└── replit.md          # This documentation file
```

## Products Sold
- **Telegram Accounts** (by country) - OTP listening enabled
- **Gmail Accounts** - 150 credits (default, configurable)
- **WhatsApp Accounts** - 120 credits (default, configurable)

## Configuration
All sensitive configuration is stored in Replit Secrets:
- `API_ID` - Telegram API ID from https://my.telegram.org
- `API_HASH` - Telegram API Hash from https://my.telegram.org
- `BOT_TOKEN` - Bot token from @BotFather
- `ADMIN_ID` - Telegram user ID of the main admin
- `LOG_GROUP_ID` - Telegram group ID for logging
- `MONGO_DB_URI` - MongoDB connection string

## Database Collections
- `users` - User profiles, balances, and referrals
- `sessions` - Available session files by country
- `countries` - Country list with flags and names
- `prices` - Pricing for each country
- `admins` - List of admin user IDs
- `agents` - List of agent user IDs (limited permissions)
- `stats` - Sales statistics (total/daily)
- `redeem_codes` - Redemption codes for free credits
- `active_otp_listeners` - Currently active OTP listeners
- `deposit_requests` - Pending deposit approvals
- `sell_logs` - Transaction history
- `assigned_sessions` - Sessions assigned to users for OTP
- `settings` - Bot settings (referral credit amount)

## Admin Commands

### Gmail Account Management
- `/addgmail <email> <password>` - Add Gmail account to stock
- `/gmailstock` - View all Gmail accounts in inventory
- `/setgmailprice <amount>` - Change Gmail price (default: 150 credits)
- `/gmailhelp` - Complete guide with examples (FULL TUTORIAL)

### WhatsApp Account Management
- `/addwhatsapp <phone> <backup_code>` - Add WhatsApp account to stock
- `/whatsappstock` - View all WhatsApp accounts in inventory
- `/setwhatsappprice <amount>` - Change WhatsApp price (default: 120 credits)
- `/whatsapphelp` - Complete guide with examples (FULL TUTORIAL)

### User Management
- `/addcredit <user_id> <amount>` - Add credits to user
- `/removecredit <user_id> <amount>` - Remove credits from user
- `/ban <user_id>` - Ban a user from using the bot
- `/unban <user_id>` - Unban a user
- `/user <user_id>` - View detailed user information
- `/users` - List top 20 users by balance
- `/leaderboard` - Show top users by balance & referrals

### Country & Pricing Management
- `/addcountry <code> <name> <price>` - Add a new country
- `/removecountry <code>` - Remove a country
- `/setprice <country> <price>` - Update country price
- `/upload <country>` - Upload session file (reply to .session or .zip)

### Redeem Code Management
- `/createcode <amount> <uses>` - Create redeem code (expires in 30 days)
- `/deletecode <code>` - Delete a redeem code
- `/codes` - List all active redeem codes

### Statistics & Monitoring
- `/stats` - View comprehensive bot statistics
- `/stock` - View session stock by country
- `/deposits` - View pending deposit requests

### Settings & Configuration
- `/setref <amount>` - Set referral bonus amount
- `/addadmin <user_id>` - Add an admin (owner only)

### Communication
- `/broadcast <message>` - Broadcast message to all users

### Help & Information
- `/admin` - Display all admin commands with descriptions

## Agent System
Agents are users with limited administrative permissions. They can help manage inventory without having full admin access.

### Agent Commands (Admin Only)
- `/addagent <user_id>` - Grant agent permissions to a user
- `/rmagent <user_id>` - Revoke agent permissions from a user
- `/agents` - View list of all current agents

### What Agents Can Do
- **View Stock** - Use `/stock` to check available sessions by country
- **Upload Sessions** - Use `/upload <country>` to add new session files

### What Agents Cannot Do
- Cannot manage users (add/remove credits, ban/unban)
- Cannot manage pricing or countries
- Cannot view statistics or deposits
- Cannot create redeem codes
- Cannot broadcast messages
- Cannot manage other agents or admins

### Agent Notifications
- Agents receive a notification when they are added or removed
- All agent upload activities are logged to the admin group

## User Features
- Buy accounts from available countries
- Automatic OTP code delivery
- Referral system to earn credits
- Deposit via UPI or Crypto
- Profile with balance and stats
- Redeem codes for free credits

## How OTP System Works
1. User purchases an account
2. User receives phone number
3. User clicks "VIEW OTP" button
4. Bot starts Telethon listener on the session
5. When Telegram sends OTP (from user 777000), bot captures it
6. Bot automatically forwards OTP to user
7. User enters OTP in Telegram app to complete login

## Gmail & WhatsApp Accounts System

### How Admins Add Gmail Accounts
```
/addgmail user@gmail.com mypassword123
```
- Format: `/addgmail <email> <password>`
- Account added instantly to stock
- Logged to admin group
- Shows in `/gmailstock`

### How Admins Add WhatsApp Accounts
```
/addwhatsapp +919876543210 ABCD-1234-EFGH-5678
```
- Format: `/addwhatsapp <phone_number> <backup_code>`
- Account added instantly to stock
- Logged to admin group
- Shows in `/whatsappstock`

### How Users Buy Accounts
**Gmail Purchase Flow:**
1. User clicks 💌 Gmail button
2. Bot checks user balance
3. If balance ≥ Gmail price, sale completes instantly
4. User receives: Email + Password in private message
5. Account removed from stock

**WhatsApp Purchase Flow:**
1. User clicks 💬 WhatsApp button
2. Bot checks user balance
3. If balance ≥ WhatsApp price, sale completes instantly
4. User receives: Phone Number + Backup Code in private message
5. Account removed from stock

### Price Management
- Default Gmail Price: 150 credits
- Default WhatsApp Price: 120 credits
- Change anytime with `/setgmailprice <amount>` or `/setwhatsappprice <amount>`
- All users see new price immediately
- Logged to admin group

### Complete Guides Available
- `/gmailhelp` - Full tutorial with all examples
- `/whatsapphelp` - Full tutorial with all examples
- `/admin` - Shows current prices

## Recent Changes
- **2025-11-10**: Enhanced Sell Logging System
  - Session files are now automatically sent to log group when account is sold
  - Log includes session file with buyer information
  - Helps admins track sold sessions and maintain backups

- **2025-11-10**: Added Agent Role System
  - Created new **Agent** role with limited permissions
  - Added `/addagent <user_id>` - Assign agent role to users
  - Added `/rmagent <user_id>` - Remove agent role from users
  - Added `/agents` - List all active agents
  - Agents can **only** use `/stock` and `/upload` commands
  - Modified `/stock` and `/upload` to allow agent access
  - Agents receive notifications when added/removed
  - All agent activities logged to admin group
  
- **2025-11-10**: Enhanced with powerful admin commands
  - Added `/addcredit` - Add credits to users
  - Added `/ban` and `/unban` - Ban/unban users
  - Added `/user` and `/users` - View user information
  - Added `/stats` - Comprehensive bot statistics
  - Added `/stock` - View session inventory by country
  - Added `/deposits` - Monitor pending deposits
  - Added `/broadcast` - Send messages to all users
  - Added `/createcode`, `/deletecode`, `/codes` - Manage redeem codes
  - Added `/setprice` and `/setref` - Update pricing and referral bonus
  - Added `/admin` - Help command showing all admin commands
  - Added ban check middleware to prevent banned users from using bot

- **2025-11-10**: Imported from GitHub and configured for Replit environment
  - Moved all credentials to environment variables for security
  - Added .gitignore for Python project
  - Installed all dependencies
  - Set up workflow for bot execution

## Running the Bot
The bot runs automatically via the configured workflow. It will:
1. Connect to MongoDB
2. Initialize database collections
3. Start listening for Telegram messages
4. Process user commands and callbacks

## Development Notes
- The bot uses both Pyrogram (for bot operations) and Telethon (for OTP listening)
- Session files are stored in `sessions/` directory
- Temporary files are stored in `temp/` directory
- Logs are written to `bot.log` and console

## User Preferences
None specified yet.

## Architecture Notes
- Async/await throughout using asyncio
- MongoDB for persistent storage
- In-memory cache for active OTP listeners
- Auto-cleanup of daily stats at midnight
