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

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# কনভারসেশন স্টেট
WAITING_USERNAMES, WAITING_PASSWORD, WAITING_2FA, CONFIRM_EXTRACTION = range(4)

class InstagramCookieBot:
    """ইনস্টাগ্রাম কুকি এক্সট্রাক্টর বট"""
    
    def __init__(self, token):
        self.app = Application.builder().token(token).build()
        self.extractor = InstagramCookieExtractor()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """হ্যান্ডলার সেটআপ"""
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start_command),
                CallbackQueryHandler(self.start_command, pattern='^start_extraction$')
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
        )
        self.app.add_handler(conv_handler)
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """স্টার্ট কমান্ড"""
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
        
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                welcome, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                welcome, 
                reply_markup=reply_markup, 
                parse_mode=ParseMode.HTML
            )
        return WAITING_USERNAMES
    
    async def receive_usernames(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ইউজারনেম গ্রহণ - ধাপ ১/৩"""
        message_text = update.message.text.strip()
        
        # ইউজারনেম আলাদা করা (প্রতি লাইনে একটি)
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
        
        summary += "\n✔ <b>ধাপ ২/৩ — পাসওয়ার্ড দিন</b>\n<i>(সব অ্যাকাউন্টের জন্য একই পাসওয়ার্ড)</i>"
        
        keyboard = [[InlineKeyboardButton("❌ বাতিল", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            summary, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.HTML
        )
        return WAITING_PASSWORD
    
    async def receive_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """পাসওয়ার্ড গ্রহণ - ধাপ ২/৩"""
        password = update.message.text.strip()
        
        # নিরাপত্তার জন্য মেসেজ ডিলিট
        try:
            await update.message.delete()
        except:
            pass
        
        context.user_data['password'] = password
        
        keyboard = [[InlineKeyboardButton("❌ বাতিল", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔒 <b>পাসওয়ার্ড সংরক্ষিত</b>\n\n"
            "✔ <b>ধাপ ৩/৩ — 2FA রিকভারি কী দিন</b>\n\n"
            "<i>2FA চালু না থাকলে 'none' লিখুন।</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_2FA
    
    async def receive_2fa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """2FA কী গ্রহণ - ধাপ ৩/৩"""
        two_fa_key = update.message.text.strip()
        
        # মেসেজ ডিলিট
        try:
            await update.message.delete()
        except:
            pass
        
        if two_fa_key.lower() in ['none', 'n/a', 'na', 'no', '-']:
            two_fa_key = None
        
        context.user_data['two_factor_key'] = two_fa_key
        
        usernames = context.user_data['usernames']
        summary = "📊 <b>অ্যাকাউন্ট সামারি:</b>\n\n"
        
        for idx, username in enumerate(usernames, 1):
            fa_status = "✅ 2FA কী আছে" if two_fa_key else "⚠️ 2FA কী নেই"
            summary += f"✔ {idx}. {username} — {fa_status}\n"
        
        summary += (
            f"\n{'─' * 30}\n"
            f"📝 <b>মোট:</b> {len(usernames)}টি প্রসেস হবে\n"
            f"⏭ <b>বাদ যাবে:</b> 0টি\n\n"
            f"⚠️ <b>কনফার্ম করুন</b>"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ নিশ্চিত করুন", callback_data='confirm'),
                InlineKeyboardButton("❌ বাতিল", callback_data='cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            summary,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return CONFIRM_EXTRACTION
    
    async def confirm_extraction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """এক্সট্রাকশন কনফার্ম ও শুরু"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔄 <b>প্রসেসিং হচ্ছে...</b>\n\n⏳ অনুগ্রহ করে অপেক্ষা করুন।",
            parse_mode=ParseMode.HTML
        )
        
        usernames = context.user_data['usernames']
        password = context.user_data['password']
        two_factor_key = context.user_data.get('two_factor_key')
        
        results = []
        
        for idx, username in enumerate(usernames, 1):
            # প্রোগ্রেস আপডেট
            try:
                await query.message.edit_text(
                    f"⏳ <b>প্রসেসিং: {idx}/{len(usernames)}</b>\n👤 {username}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            # Instagram থেকে কুকি এক্সট্রাক্ট
            result = self.extractor.extract_cookies(
                username=username,
                password=password,
                two_factor_key=two_factor_key
            )
            
            if result['success']:
                # গুরুত্বপূর্ণ কুকি দেখানো
                cookies_json = json.dumps(
                    result.get('important_cookies', result.get('cookies', {})), 
                    indent=2
                )
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=(
                        f"✅ <b>{username} — সফল!</b>\n\n"
                        f"<b>কুকি:</b>\n<pre>{cookies_json}</pre>"
                    ),
                    parse_mode=ParseMode.HTML
                )
                
                # JSON ফাইল হিসেবে সম্পূর্ণ কুকি পাঠানো
                full_cookies = json.dumps(result['cookies'], indent=2)
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=full_cookies.encode('utf-8'),
                    filename=f"{username}_cookies.json",
                    caption=f"📎 {username} এর সম্পূর্ণ কুকি"
                )
                
                results.append(f"✅ {username}")
            else:
                error_msg = result.get('error', 'অজানা এরর')
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"❌ <b>{username} — ব্যর্থ</b>\nকারণ: {error_msg}",
                    parse_mode=ParseMode.HTML
                )
                results.append(f"❌ {username}")
        
        # ফাইনাল রিপোর্ট
        final_report = "📊 <b>এক্সট্রাকশন সম্পন্ন!</b>\n\n"
        for res in results:
            final_report += f"{res}\n"
        
        final_report += "\n🔒 <b>সব সংবেদনশীল ডাটা মুছে ফেলা হয়েছে</b>"
        
        keyboard = [
            [InlineKeyboardButton("🔄 নতুন এক্সট্রাকশন", callback_data='start_extraction')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=final_report,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # সংবেদনশীল ডাটা ক্লিয়ার
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ক্যান্সেল কমান্ড"""
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        
        await update.message.reply_text(
            "❌ <b>প্রক্রিয়া বাতিল করা হয়েছে</b>\n\n"
            "সব ডাটা মুছে ফেলা হয়েছে।\n"
            "/start দিয়ে আবার শুরু করুন।",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    
    async def cancel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ক্যান্সেল বাটন"""
        query = update.callback_query
        await query.answer()
        
        for key in ['password', 'two_factor_key', 'usernames']:
            context.user_data.pop(key, None)
        
        await query.edit_message_text(
            "❌ <b>বাতিল করা হয়েছে</b>\n\n/start দিয়ে আবার শুরু করুন।",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """এরর হ্যান্ডলার"""
        logger.error(f"এরর ঘটেছে: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ <b>একটি এরর ঘটেছে</b>\n\nদয়া করে /start দিয়ে আবার চেষ্টা করুন।",
                parse_mode=ParseMode.HTML
            )
    
    def run(self):
        """বট রান"""
        print("🤖 Instagram Cookie Extractor Bot শুরু হচ্ছে...")
        print("✅ বট চালু!")
        self.app.run_polling(drop_pending_updates=True)


# মেইন
if __name__ == "__main__":
    # টোকেন চেক
    if not config.BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN সেট করা নেই! Railway Variables-এ BOT_TOKEN অ্যাড করুন।")
    
    # বট স্টার্ট
    bot = InstagramCookieBot(config.BOT_TOKEN)
    bot.run()
