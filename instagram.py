# instagram.py
import requests
import json
import time
import re
import sys
import config

class InstagramCookieExtractor:
    """Requests দিয়ে Instagram কুকি এক্সট্রাক্টর"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.INSTAGRAM_HEADERS)
        self.current_username = None
    
    def log(self, msg):
        """লগ মেসেজ প্রিন্ট"""
        print(f"[INSTA] {msg}", flush=True)
    
    def _get_csrf_token(self):
        """CSRF ও অন্যান্য টোকেন সংগ্রহ"""
        try:
            self.log("Instagram হোমপেজ লোড হচ্ছে...")
            response = self.session.get("https://www.instagram.com/")
            self.log(f"হোমপেজ স্ট্যাটাস: {response.status_code}")
            
            csrf_token = None
            csrf_match = re.search(r'"csrf_token":"(.*?)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                self.session.headers.update({"X-CSRFToken": csrf_token})
                self.log(f"CSRF পাওয়া গেছে: {csrf_token[:15]}...")
            else:
                for cookie in self.session.cookies:
                    if cookie.name == 'csrftoken':
                        csrf_token = cookie.value
                        self.session.headers.update({"X-CSRFToken": csrf_token})
                        self.log("CSRF কুকি থেকে পাওয়া গেছে")
                        break
            
            if not csrf_token:
                self.log("CSRF টোকেন পাওয়া যায়নি!")
                return None
            
            # এক্সট্রা হেডার
            self.session.headers.update({
                "X-IG-App-Locale": "en_US",
                "X-IG-Device-Locale": "en_US",
            })
            
            return csrf_token
        except Exception as e:
            self.log(f"CSRF এরর: {e}")
            return None
    
    def _encrypt_password(self, password):
        """Instagram পাসওয়ার্ড এনক্রিপশন"""
        return f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}"
    
    def _handle_2fa(self, two_factor_key, two_factor_identifier):
        """2FA হ্যান্ডেল"""
        try:
            try:
                import pyotp
                clean_key = two_factor_key.replace(" ", "").upper()
                totp = pyotp.TOTP(clean_key)
                verification_code = totp.now()
                self.log(f"2FA কোড: {verification_code}")
            except Exception as e:
                self.log(f"pyotp এরর: {e}")
                return False
            
            two_factor_data = {
                "verification_code": verification_code,
                "two_factor_identifier": two_factor_identifier,
                "username": self.current_username,
                "trust_this_device": "1",
                "verification_method": "3"
            }
            
            response = self.session.post(
                "https://www.instagram.com/api/v1/web/accounts/login/ajax/two_factor/",
                data=two_factor_data,
                headers={"X-CSRFToken": self.session.headers.get("X-CSRFToken")}
            )
            
            self.log(f"2FA রেসপন্স: {response.text[:300]}")
            return response.json().get("authenticated", False)
        except Exception as e:
            self.log(f"2FA এরর: {e}")
            return False
    
    def extract_cookies(self, username, password, two_factor_key=None):
        """মেইন এক্সট্রাকশন ফাংশন"""
        result = {
            "success": False,
            "username": username,
            "cookies": None,
            "important_cookies": None,
            "error": None
        }
        
        self.current_username = username
        self.log(f"=== {username} শুরু ===")
        
        try:
            # CSRF টোকেন
            csrf_token = self._get_csrf_token()
            if not csrf_token:
                result["error"] = "CSRF টোকেন পাওয়া যায়নি"
                return result
            
            time.sleep(2)
            
            # লগইন
            self.log(f"লগইন চেষ্টা: {username}")
            login_data = {
                "username": username,
                "enc_password": self._encrypt_password(password),
                "queryParams": "{}",
                "optIntoOneTap": "false",
            }
            
            login_response = self.session.post(
                config.INSTAGRAM_LOGIN_URL,
                data=login_data,
                headers={
                    "X-CSRFToken": csrf_token,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            
            self.log(f"লগইন স্ট্যাটাস: {login_response.status_code}")
            self.log(f"লগইন রেসপন্স: {login_response.text[:500]}")
            
            login_result = login_response.json()
            
            if login_result.get("authenticated"):
                self.log("লগইন সফল!")
            elif login_result.get("two_factor_required"):
                self.log("2FA প্রয়োজন")
                if two_factor_key:
                    two_factor_id = login_result.get("two_factor_info", {}).get("two_factor_identifier")
                    if not two_factor_id or not self._handle_2fa(two_factor_key, two_factor_id):
                        result["error"] = "2FA ভেরিফিকেশন ব্যর্থ"
                        return result
                else:
                    result["error"] = "2FA প্রয়োজন কিন্তু কী দেওয়া হয়নি"
                    return result
            elif login_result.get("checkpoint_required"):
                result["error"] = "চেকপয়েন্ট প্রয়োজন - Instagram সিকিউরিটি চেক"
                return result
            elif login_result.get("message") == "challenge_required":
                result["error"] = "চ্যালেঞ্জ প্রয়োজন - Instagram ভেরিফিকেশন চায়"
                return result
            else:
                error_msg = login_result.get("message", "অজানা এরর")
                result["error"] = f"Instagram: {error_msg}"
                return result
            
            # কুকি সংগ্রহ
            self.log("কুকি সংগ্রহ হচ্ছে...")
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
                if cookie.name in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did']:
                    important_cookies[cookie.name] = cookie.value
                    self.log(f"গুরুত্বপূর্ণ কুকি: {cookie.name} = {cookie.value[:20]}...")
            
            if 'sessionid' not in important_cookies:
                self.log("সতর্কতা: sessionid পাওয়া যায়নি!")
                result["error"] = "sessionid কুকি পাওয়া যায়নি"
                return result
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            self.log(f"সফল! {len(important_cookies)}টি গুরুত্বপূর্ণ কুকি")
            
        except json.JSONDecodeError as e:
            result["error"] = f"JSON পার্সিং এরর: {e}"
            self.log(f"JSON এরর: {e}")
        except Exception as e:
            result["error"] = f"এরর: {str(e)}"
            self.log(f"এক্সেপশন: {e}")
        
        self.log(f"=== {username} শেষ ({'সফল' if result['success'] else 'ব্যর্থ'}) ===")
        return result
