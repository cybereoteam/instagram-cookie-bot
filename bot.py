from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from instagram_login import extract_cookies
import os

# Bot states
USERNAME, PASSWORD, TWO_FA = range(3)

# Start message
def start(update: Update, _: CallbackContext):
    update.message.reply_text(
        "🍪 Welcome to Instagram Cookie Extractor Bot!\n\n"
        "This bot extracts session cookies from Instagram accounts.\n\n"
        "📩 Click 'Start' to begin!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Start", callback_data="begin")]])
    )

# Step 1: Get Instagram username(s)
def start_extraction(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🖊️ Step 1/3: Please send the Instagram username(s):\n\n"
        "Format:\n - For single account: `username`\n - For multiple accounts (one per line):\n`user1\nuser2\nuser3`\n\n"
        "*Send your username(s), and click Cancel anytime to stop.*",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return USERNAME

# Step 2: Get the password
def receive_usernames(update: Update, context: CallbackContext):
    context.user_data["usernames"] = update.message.text.strip().split("\n")
    usernames = "\n".join(context.user_data["usernames"])
    update.message.reply_text(
        f"✅ Usernames received:\n{usernames}\n\n"
        "🔑 Step 2/3: Please send the password (same password used across all accounts):",
        parse_mode="Markdown"
    )
    return PASSWORD

# Step 3: Get the 2FA code
def receive_password(update: Update, context: CallbackContext):
    context.user_data["password"] = update.message.text.strip()
    update.message.reply_text("🔒 Step 3/3: Please send the Two-Factor Authentication (2FA) code:")
    return TWO_FA

# Final Step: Process login and extract cookies
def process_accounts(update: Update, context: CallbackContext):
    usernames = context.user_data["usernames"]
    password = context.user_data["password"]
    two_factor_code = update.message.text.strip()

    for username in usernames:
        try:
            extract_cookies(username, password, two_factor_code)
            update.message.reply_text(f"✅ Successfully extracted cookies for: {username}")
        except Exception as e:
            update.message.reply_text(f"❌ Failed to extract cookies for {username}. Reason: {str(e)}")

    return ConversationHandler.END

# Cancel the process
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Process canceled.")
    return ConversationHandler.END

# Main bot function
def main():
    # Load bot token from the configuration file
    with open("config.json", "r") as file:
        config = json.load(file)
    updater = Updater(config["telegram_bot_token"], use_context=True)
    
    dispatcher = updater.dispatcher

    # Set up conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            USERNAME: [MessageHandler(Filters.text & ~Filters.command, receive_usernames)],
            PASSWORD: [MessageHandler(Filters.text & ~Filters.command, receive_password)],
            TWO_FA: [MessageHandler(Filters.text & ~Filters.command, process_accounts)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(conv_handler)

    print("Bot is running... Press CTRL+C to stop.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
