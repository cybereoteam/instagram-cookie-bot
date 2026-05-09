# config.py
import os
import sys

# Railway Environment Variable থেকে টোকেন নেওয়া
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("=" * 50)
    print("❌ এরর: BOT_TOKEN সেট করা নেই!")
    print("Railway Dashboard → Variables → Add BOT_TOKEN")
    print("=" * 50)
    sys.exit(1)

print(f"✅ BOT_TOKEN লোড হয়েছে: {BOT_TOKEN[:10]}...")

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
