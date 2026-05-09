# instagram.py
import json
import time
import random
from playwright.sync_api import sync_playwright

class InstagramCookieExtractor:
    """Playwright দিয়ে Instagram কুকি এক্সট্রাক্টর"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    def log(self, msg):
        print(f"[INSTA] {msg}", flush=True)
    
    def _random_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def extract_cookies(self, username, password, two_factor_key=None):
        result = {
            "success": False,
            "username": username,
            "cookies": None,
            "important_cookies": None,
            "error": None
        }
        
        self.log(f"{'='*10} {username} - শুরু {'='*10}")
        
        try:
            # Playwright স্টার্ট
            self.log("ব্রাউজার চালু হচ্ছে...")
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # মোবাইল ইউজার এজেন্ট
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                viewport={"width": 390, "height": 844}
            )
            self.page = self.context.new_page()
            
            # Instagram লগইন পেজ
            self.log("Instagram খোলা হচ্ছে...")
            self.page.goto("https://www.instagram.com/accounts/login/")
            self._random_delay(3, 5)
            
            # ইউজারনেম
            self.log("ইউজারনেম দেওয়া হচ্ছে...")
            self.page.fill("input[name='username']", username)
            self._random_delay(1, 2)
            
            # পাসওয়ার্ড
            self.log("পাসওয়ার্ড দেওয়া হচ্ছে...")
            self.page.fill("input[name='password']", password)
            self._random_delay(1, 2)
            
            # লগইন
            self.log("লগইন বাটনে ক্লিক...")
            self.page.click("button[type='submit']")
            self._random_delay(5, 8)
            
            # 2FA চেক
            if "challenge" in self.page.url or "two_factor" in self.page.url:
                self.log("2FA প্রয়োজন")
                
                if two_factor_key:
                    verification_code = None
                    
                    if two_factor_key.strip().isdigit() and len(two_factor_key.strip()) == 6:
                        verification_code = two_factor_key.strip()
                        self.log(f"ম্যানুয়াল কোড: {verification_code}")
                    else:
                        try:
                            import pyotp
                            clean_key = two_factor_key.replace(" ", "").upper()
                            totp = pyotp.TOTP(clean_key)
                            verification_code = totp.now()
                            self.log(f"TOTP কোড: {verification_code}")
                        except:
                            result["error"] = "2FA কোড জেনারেট ব্যর্থ"
                            return result
                    
                    # কোড ইনপুট
                    self.page.fill("input[name='verificationCode']", verification_code)
                    self._random_delay(1, 2)
                    self.page.click("button:has-text('Submit'), button:has-text('Confirm')")
                    self._random_delay(5, 8)
                else:
                    result["error"] = "2FA প্রয়োজন"
                    return result
            
            # লগইন চেক
            if "login" in self.page.url:
                result["error"] = "লগইন ব্যর্থ"
                return result
            
            self.log("লগইন সফল!")
            self._random_delay(2, 3)
            
            # কুকি
            self.log("কুকি সংগ্রহ...")
            cookies = self.context.cookies()
            
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in cookies:
                cookies_dict[cookie['name']] = cookie['value']
                if cookie['name'] in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did']:
                    important_cookies[cookie['name']] = cookie['value']
                    self.log(f"  {cookie['name']}: {cookie['value'][:25]}...")
            
            if 'sessionid' not in important_cookies:
                result["error"] = "sessionid পাওয়া যায়নি"
                return result
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            self.log(f"সফল! কুকি: {list(important_cookies.keys())}")
            
        except Exception as e:
            result["error"] = f"এরর: {str(e)[:100]}"
            self.log(f"এক্সেপশন: {e}")
        
        finally:
            if self.browser:
                self.browser.close()
        
        return result
