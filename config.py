# config.py
import os

# টোকেন ম্যানুয়ালি ইনপুট নেওয়া
print("=" * 50)
print("🔑 আপনার Telegram Bot Token দিন")
print("=" * 50)
BOT_TOKEN = input("Token: ").strip()

if not BOT_TOKEN:
    print("❌ টোকেন দেওয়া হয়নি! আবার চেষ্টা করুন।")
    exit(1)

print(f"✅ টোকেন লোড হয়েছে: {BOT_TOKEN[:15]}...")

# Instagram সেটিংস
INSTAGRAM_LOGIN_URL = "https://www.instagram.com/api/v1/web/accounts/login/ajax/"
INSTAGRAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
