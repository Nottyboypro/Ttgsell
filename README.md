# Telegram Session Bot

A feature-rich Telegram bot for managing and selling Telegram session accounts with automatic OTP listening functionality.

## Features

### For Users
- **Buy Accounts**: Purchase Telegram accounts from various countries
- **Automatic OTP**: Get OTP codes automatically without sharing session files
- **Referral System**: Earn credits by inviting friends
- **Multiple Payment Methods**: UPI and Crypto deposits supported
- **User Profile**: Track balance, spending, and referrals

### For Admins
- **Country Management**: Add/remove countries and set prices
- **User Management**: Add/remove credits, manage admins
- **Deposit Approval**: Review and approve payment screenshots
- **Statistics Dashboard**: Track sales and revenue
- **Broadcast Messages**: Send announcements to all users
- **Redeem Codes**: Generate promotional codes

## Setup Instructions

### Prerequisites
1. **Telegram API Credentials**
   - Go to https://my.telegram.org
   - Create an application to get API_ID and API_HASH

2. **Telegram Bot**
   - Message @BotFather on Telegram
   - Create a new bot to get BOT_TOKEN

3. **MongoDB Database**
   - Create a free MongoDB Atlas cluster at https://www.mongodb.com/cloud/atlas
   - Get your connection string

4. **Log Group**
   - Create a Telegram group for logs
   - Add your bot to the group
   - Get the group ID (use @RawDataBot)

### Environment Variables
Set these in Replit Secrets:
- `API_ID` - Your Telegram API ID
- `API_HASH` - Your Telegram API Hash
- `BOT_TOKEN` - Your bot token from BotFather
- `ADMIN_ID` - Your Telegram user ID
- `LOG_GROUP_ID` - Group ID for logs
- `MONGO_DB_URI` - MongoDB connection string

### Running the Bot
The bot runs automatically when you start the Repl. Check the console for status messages.

## User Commands

### Basic Commands
- `/start` - Start the bot and see main menu
- `/redeem <code>` - Redeem a promotional code

### Menu Options
- **Buy Account** - Browse and purchase accounts
- **Refer & Earn** - Get your referral link
- **Redeem Code** - Enter redeem codes
- **Deposit Money** - Add credits (UPI/Crypto)
- **Profile** - View your stats

## Admin Commands

### Country Management
```
/addcountry <code> <name> <price>
Example: /addcountry usa "United States" 150
```

```
/removecountry <code>
Example: /removecountry usa
```

```
/setprice <country> <price>
Example: /setprice usa 200
```

### Credit Management
```
/addcredit <user_id> <amount>
Example: /addcredit 123456789 100
```

```
/removecredit <user_id> <amount>
Example: /removecredit 123456789 50
```

### Session Management
```
/upload <country>
Reply to a .session file or .zip containing sessions
Example: Reply to file with "/upload usa"
```

### Promotional Codes
```
/createcode <amount> <max_uses>
Example: /createcode 100 50
```

### Settings
```
/setref <amount>
Example: /setref 75
Sets referral bonus amount
```

### Admin Management
```
/addadmin <user_id>
Example: /addadmin 987654321
```

### Statistics
```
/stats
Shows bot statistics and revenue
```

### Broadcasting
```
/broadcast <message>
Example: /broadcast Welcome to our new feature!
```

## How OTP System Works

1. User buys an account from a country
2. Bot assigns a phone number to the user
3. User attempts to login with the phone number in Telegram app
4. User clicks "VIEW OTP" button in the bot
5. Bot starts listening for OTP using Telethon
6. When OTP arrives (from Telegram service), bot captures it
7. Bot sends OTP directly to user
8. User enters OTP in Telegram app to complete login

**Security Note**: Session files are never sent to users, only phone numbers and OTP codes.

## Payment Methods

### UPI Payment
1. Click "Deposit Money" → "UPI Payment"
2. Send payment to provided UPI ID
3. Take a screenshot of the payment
4. Send screenshot with amount as caption
5. Wait for admin approval

### Crypto Payment
1. Click "Deposit Money" → "Crypto Payment"
2. Send USDT to provided wallet address (TRC20/BEP20)
3. Take a screenshot of transaction
4. Send screenshot with USDT amount as caption
5. Wait for admin approval

## Database Structure

The bot uses MongoDB with the following collections:
- `users` - User accounts and balances
- `sessions` - Available session inventory
- `countries` - Country configurations
- `prices` - Pricing data
- `admins` - Admin user IDs
- `stats` - Sales statistics
- `redeem_codes` - Active redeem codes
- `deposit_requests` - Pending deposits
- `assigned_sessions` - User session assignments
- `settings` - Bot configuration

## Technical Stack

- **Python 3.11**
- **Pyrogram 2.0.106** - Telegram Bot API
- **Telethon 1.28.5** - OTP listening
- **Motor 3.3.2** - Async MongoDB driver
- **MongoDB** - Database

## File Structure

```
.
├── bot.py              # Main application
├── requirements.txt    # Python dependencies
├── sessions/          # Session files storage
├── temp/              # Temporary files
├── .gitignore         # Git ignore rules
├── README.md          # This file
└── replit.md          # Replit documentation
```

## Support

For issues or questions, contact the bot admin.

## License

This project is for educational purposes. Use responsibly and in accordance with Telegram's Terms of Service.
