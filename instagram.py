# instagram.py
import requests
import json
import time
import re
import config

class InstagramCookieExtractor:
    """Requests দিয়ে Instagram কুকি এক্সট্রাক্টর"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.INSTAGRAM_HEADERS)
        self.current_username = None
    
    def _get_csrf_token(self):
        """CSRF ও অন্যান্য টোকেন সংগ্রহ"""
        try:
            response = self.session.get("https://www.instagram.com/")
            
            csrf_token = None
            csrf_match = re.search(r'"csrf_token":"(.*?)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                self.session.headers.update({"X-CSRFToken": csrf_token})
            else:
                for cookie in self.session.cookies:
                    if cookie.name == 'csrftoken':
                        csrf_token = cookie.value
                        self.session.headers.update({"X-CSRFToken": csrf_token})
                        break
            
            # নতুন Instagram হেডার
            self.session.headers.update({
                "X-IG-App-Locale": "en_US",
                "X-IG-Device-Locale": "en_US",
            })
            
            return csrf_token
        except Exception as e:
            print(f"CSRF এরর: {e}")
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
            except:
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
            
            return response.json().get("authenticated", False)
        except:
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
        
        try:
            # CSRF টোকেন
            csrf_token = self._get_csrf_token()
            if not csrf_token:
                result["error"] = "CSRF টোকেন পাওয়া যায়নি"
                return result
            
            time.sleep(2)
            
            # লগইন
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
            
            login_result = login_response.json()
            
            if login_result.get("authenticated"):
                pass  # সফল
            elif login_result.get("two_factor_required"):
                if two_factor_key:
                    two_factor_id = login_result.get("two_factor_info", {}).get("two_factor_identifier")
                    if not two_factor_id or not self._handle_2fa(two_factor_key, two_factor_id):
                        result["error"] = "2FA ভেরিফিকেশন ব্যর্থ"
                        return result
                else:
                    result["error"] = "2FA প্রয়োজন কিন্তু কী দেওয়া হয়নি"
                    return result
            else:
                result["error"] = login_result.get("message", "লগইন ব্যর্থ")
                return result
            
            # কুকি সংগ্রহ
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
                if cookie.name in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did']:
                    important_cookies[cookie.name] = cookie.value
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            
        except Exception as e:
            result["error"] = f"এরর: {str(e)}"
        
        return result
