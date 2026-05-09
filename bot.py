# bot.py
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
import config
from instagram import InstagramCookieExtractor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WAITING_USERNAMES, WAITING_PASSWORD, WAITING_2FA, CONFIRM_EXTRACTION = range(4)

class InstagramCookieBot:
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.extractor = InstagramCookieExtractor()
        self._setup_handlers()
    
    def _setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start_command),
                CallbackQueryHandler(self.start_button_callback, pattern='^start_extraction$')
            ],
            states={
                WAITING_USERNAMES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_usernames),
                    CallbackQueryHandler(self.cancel_callback, pattern='^cancel$')
                ],
                WAITING_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_password),
                    CallbackQueryHandler(self.cancel_callback, pattern='^cancel$')
                ],
                WAITING_2FA: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_2fa),
                    CallbackQueryHandler(self.cancel_callback, pattern='^cancel$')
                ],
                CONFIRM_EXTRACTION: [
                    CallbackQueryHandler(self.confirm_extraction, pattern='^confirm$'),
                    CallbackQueryHandler(self.cancel_callback, pattern='^cancel$')
                ],
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)],
            per_message=False
        )
        self.app.add_handler(conv_handler)
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        welcome = (
            "🔐 <b>Instagram Cookie Extractor Bot</b>\n\n"
            "📋 <b>যা করতে হবে:</b>\n"
            "1️⃣ Instagram ইউজারনেম(গুলি) দিন\n"
            "2️⃣ পাসওয়ার্ড দিন\n"
            "3️⃣ 2FA কী দিন (থাকলে)\n\n"
            "⚠️ <b>আপনার তথ্য নিরাপদ থাকবে</b>"
        )
        keyboard = [[InlineKeyboardButton("🚀 শুরু করুন", callback_data='start_extraction')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return WAITING_USERNAMES
    
    async def start_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data.clear()
        welcome = (
            "🔐 <b>Instagram Cookie Extractor Bot</b>\n\n"
            "📋 <b>যা করতে হবে:</b>\n"
            "1️⃣ Instagram ইউজারনেম(গুলি) দিন\n"
            "2️⃣ পাসওয়ার্ড দিন\n"
            "3️⃣ 2FA কী দিন (থাকলে)\n\n"
            "⚠️ <b>আপনার তথ্য নিরাপদ থাকবে</b>"
        )
        keyboard = [[InlineKeyboardButton("🚀 শুরু করুন", callback_data='start_extraction')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return WAITING_USERNAMES
    
    async def receive_usernames(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text.strip()
        usernames = []
        for line in message_text.split('\n'):
            username = line.strip().lstrip('@')
            if username:
                usernames.append(username)
        
        if not usernames:
            await update.message.reply_text("❌ কোনো ইউজারনেম পাওয়া যায়নি। আবার দিন।")
            return WAITING_USERNAMES
        
        context.user_data['usernames'] = usernames
        summary = f"✔ <b>{len(usernames)}টি ইউজারনেম:</b>\n\n"
        for idx, username in enumerate(usernames, 1):
            summary += f"{idx}. {username}\n"
        summary += "\n✔ <b>ধাপ ২/৩ — পাসওয়ার্ড দিন</b>"
        
        keyboard = [[InlineKeyboardButton("❌ বাতিল", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return WAITING_PASSWORD
    
    async def receive_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text.strip()
        try:
            await update.message.delete()
        except:
            pass
        context.user_data['password'] = password
        
        keyboard = [[InlineKeyboardButton("❌ বাতিল", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔒 <b>পাসওয়ার্ড সংরক্ষিত</b>\n\n"
            "✔ <b>ধাপ ৩/৩ — 2FA কী দিন</b>\n"
            "<i>2FA না থাকলে 'none' লিখুন</i>",
            reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
        return WAITING_2FA
    
    async def receive_2fa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        two_fa_key = update.message.text.strip()
        try:
            await update.message.delete()
        except:
            pass
        if two_fa_key.lower() in ['none', 'n/a', 'na', 'no', '-']:
            two_fa_key = None
        context.user_data['two_factor_key'] = two_fa_key
        
        usernames = context.user_data['usernames']
        summary = "📊 <b>সামারি:</b>\n\n"
        for idx, username in enumerate(usernames, 1):
            summary += f"✔ {idx}. {username} — {'✅ 2FA আছে' if two_fa_key else '⚠️ 2FA নেই'}\n"
        summary += f"\n📝 মোট: {len(usernames)}টি\n⚠️ কনফার্ম করুন"
        
        keyboard = [
            [InlineKeyboardButton("✅ নিশ্চিত", callback_data='confirm'),
             InlineKeyboardButton("❌ বাতিল", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return CONFIRM_EXTRACTION
    
    async def confirm_extraction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("🔄 প্রসেসিং হচ্ছে...\n⏳ অপেক্ষা করুন।")
        
        usernames = context.user_data['usernames']
        password = context.user_data['password']
        two_factor_key = context.user_data.get('two_factor_key')
        results = []
        
        for idx, username in enumerate(usernames, 1):
            await query.message.edit_text(f"⏳ {username} ({idx}/{len(usernames)})")
            result = self.extractor.extract_cookies(username, password, two_factor_key)
            
            if result['success']:
                cookies_json = json.dumps(result.get('important_cookies', {}), indent=2)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ <b>{username}</b>\n<pre>{cookies_json}</pre>",
                    parse_mode=ParseMode.HTML
                )
                results.append(f"✅ {username}")
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"❌ <b>{username}</b>\n{result.get('error')}",
                    parse_mode=ParseMode.HTML
                )
                results.append(f"❌ {username}")
        
        final = "📊 <b>সম্পন্ন!</b>\n" + "\n".join(results)
        keyboard = [[InlineKeyboardButton("🔄 নতুন", callback_data='start_extraction')]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=final,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        await update.message.reply_text("❌ বাতিল। /start দিয়ে আবার শুরু করুন।")
        return ConversationHandler.END
    
    async def cancel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        await query.edit_message_text("❌ বাতিল। /start দিয়ে আবার শুরু করুন।")
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"এরর: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ এরর! /start দিয়ে আবার চেষ্টা করুন।")
    
    def run(self):
        print("🤖 Instagram Cookie Extractor Bot শুরু হচ্ছে...")
        print("✅ বট চালু!")
        self.app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN সেট করা নেই!")
    bot = InstagramCookieBot(config.BOT_TOKEN)
    bot.run()
