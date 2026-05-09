# instagram.py
import requests
import json
import time
import re
import hashlib
import uuid
import config

class InstagramCookieExtractor:
    """Instagram কুকি এক্সট্রাক্টর — ফাইনাল ফিক্সড ভার্সন"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.INSTAGRAM_HEADERS)
        self.current_username = None
        self.device_id = None
    
    def log(self, msg):
        """লগ প্রিন্ট"""
        print(f"[INSTA] {msg}", flush=True)
    
    def _generate_device_id(self, username):
        """ইউনিক ডিভাইস আইডি"""
        seed = f"android-{username}-{int(time.time())}"
        return "android-" + hashlib.md5(seed.encode()).hexdigest()[:16]
    
    def _get_csrf_token(self):
        """CSRF টোকেন সংগ্রহ — মাল্টিপল ফলব্যাক"""
        try:
            self.log("Instagram হোমপেজ লোড হচ্ছে...")
            
            response = self.session.get(
                "https://www.instagram.com/",
                headers={
                    "User-Agent": config.INSTAGRAM_HEADERS["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=15
            )
            self.log(f"হোমপেজ স্ট্যাটাস: {response.status_code}")
            
            csrf_token = None
            
            # পদ্ধতি ১: HTML থেকে
            csrf_match = re.search(r'"csrf_token":"(.*?)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                self.log(f"CSRF (HTML): {csrf_token[:15]}...")
            
            # পদ্ধতি ২: কুকি থেকে
            if not csrf_token:
                for cookie in self.session.cookies:
                    if cookie.name == 'csrftoken':
                        csrf_token = cookie.value
                        self.log("CSRF (Cookie) পাওয়া গেছে")
                        break
            
            if not csrf_token:
                self.log("CSRF টোকেন পাওয়া যায়নি!")
                return None
            
            self.session.headers.update({"X-CSRFToken": csrf_token})
            
            # ডিভাইস আইডি
            self.device_id = self._generate_device_id(self.current_username or "default")
            
            # সব প্রয়োজনীয় হেডার
            self.session.headers.update({
                "X-IG-App-ID": "936619743392459",
                "X-IG-App-Locale": "en_US",
                "X-IG-Device-Locale": "en_US",
                "X-IG-Device-ID": self.device_id,
                "X-IG-Connection-Type": "WIFI",
                "X-IG-Capabilities": "3brTv10=",
            })
            
            return csrf_token
            
        except Exception as e:
            self.log(f"CSRF এরর: {e}")
            return None
    
    def _encrypt_password(self, password):
        """Instagram স্টাইল পাসওয়ার্ড এনক্রিপশন"""
        return f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}"
    
    def _handle_2fa(self, two_factor_key, two_factor_identifier):
        """2FA ভেরিফিকেশন"""
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
            "verification_method": "3",
            "device_id": self.device_id,
            "guid": str(uuid.uuid4()),
        }
        
        response = self.session.post(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/two_factor/",
            data=two_factor_data,
            headers={
                "X-CSRFToken": self.session.headers.get("X-CSRFToken"),
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://www.instagram.com/accounts/login/",
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15
        )
        
        self.log(f"2FA স্ট্যাটাস: {response.status_code}")
        self.log(f"2FA রেসপন্স: {response.text[:300]}")
        
        result = response.json()
        
        if result.get("authenticated"):
            self.log("✅ 2FA সফল!")
            return True
        elif result.get("spam"):
            self.log("❌ Instagram স্প্যাম ডিটেক্ট করেছে")
            return False
        else:
            self.log(f"❌ 2FA ব্যর্থ: {result.get('message', '')}")
            return False
    
    def _verify_login_success(self):
        """লগইন সফল হয়েছে কিনা চেক করা"""
        try:
            # প্রথমে কুকি চেক
            has_sessionid = False
            has_ds_user_id = False
            
            for cookie in self.session.cookies:
                if cookie.name == 'sessionid':
                    has_sessionid = True
                if cookie.name == 'ds_user_id':
                    has_ds_user_id = True
            
            self.log(f"কুকি চেক: sessionid={has_sessionid}, ds_user_id={has_ds_user_id}")
            
            # sessionid থাকলে সফল
            if has_sessionid:
                return True
            
            # sessionid না থাকলে API দিয়ে চেক
            if has_ds_user_id:
                self.log("API দিয়ে লগইন ভেরিফাই করা হচ্ছে...")
                time.sleep(1)
                test_response = self.session.get(
                    "https://www.instagram.com/api/v1/accounts/current_user/",
                    headers={
                        "X-CSRFToken": self.session.headers.get("X-CSRFToken", ""),
                        "X-IG-App-ID": "936619743392459",
                    },
                    timeout=10
                )
                
                if test_response.status_code == 200:
                    user_data = test_response.json()
                    if user_data.get("user", {}).get("pk"):
                        self.log("API দিয়ে লগইন ভেরিফাইড!")
                        return True
            
            return False
            
        except Exception as e:
            self.log(f"ভেরিফিকেশন এরর: {e}")
            return False
    
    def extract_cookies(self, username, password, two_factor_key=None):
        """
        Instagram থেকে কুকি এক্সট্রাক্ট — মেইন ফাংশন
        
        Args:
            username: Instagram ইউজারনেম
            password: পাসওয়ার্ড
            two_factor_key: TOTP Secret (2FA এর জন্য, না থাকলে None)
            
        Returns:
            dict: {
                "success": True/False,
                "username": "...",
                "cookies": {...},
                "important_cookies": {...},
                "error": "..."
            }
        """
        result = {
            "success": False,
            "username": username,
            "cookies": None,
            "important_cookies": None,
            "error": None
        }
        
        self.current_username = username
        self.log(f"{'='*10} {username} - শুরু {'='*10}")
        
        try:
            # ========== ধাপ ১: CSRF টোকেন ==========
            csrf_token = self._get_csrf_token()
            if not csrf_token:
                result["error"] = "❌ Instagram সার্ভারে কানেক্ট করতে পারেনি। IP ব্লক হতে পারে।"
                return result
            
            time.sleep(2)
            
            # ========== ধাপ ২: লগইন ==========
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
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://www.instagram.com/accounts/login/",
                    "X-IG-App-ID": "936619743392459",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=15
            )
            
            self.log(f"লগইন স্ট্যাটাস: {login_response.status_code}")
            
            try:
                login_result = login_response.json()
            except:
                result["error"] = f"Instagram অজানা রেসপন্স দিয়েছে (স্ট্যাটাস: {login_response.status_code})"
                self.log(f"রেসপন্স: {login_response.text[:300]}")
                return result
            
            self.log(f"রেসপন্স: {json.dumps(login_result)[:400]}")
            
            # ========== ধাপ ৩: লগইন রেজাল্ট চেক ==========
            
            # কেস ১: সরাসরি সফল
            if login_result.get("authenticated"):
                self.log("✅ সরাসরি লগইন সফল!")
            
            # কেস ২: user=true কিন্তু authenticated=false
            elif login_result.get("user") and not login_result.get("authenticated"):
                self.log("user=true কিন্তু authenticated=false — ভেরিফাই করা হচ্ছে...")
                
                # কিছুক্ষণ অপেক্ষা
                time.sleep(3)
                
                # কুকি ইতিমধ্যে সেট হয়েছে কিনা চেক
                if self._verify_login_success():
                    self.log("✅ ভেরিফিকেশন সফল! কুকি পাওয়া গেছে।")
                else:
                    result["error"] = (
                        "⚠️ Instagram লগইন সম্পূর্ণ করতে পারেনি।\n\n"
                        "সম্ভাব্য কারণ:\n"
                        "• Railway/সার্ভারের IP ব্লকড\n"
                        "• Instagram সিকিউরিটি চেক চাইছে\n\n"
                        "💡 সমাধান: আপনার লোকাল পিসি/ল্যাপটপ থেকে বট রান করুন।"
                    )
                    return result
            
            # কেস ৩: 2FA প্রয়োজন
            elif login_result.get("two_factor_required"):
                self.log("2FA প্রয়োজন")
                
                if not two_factor_key:
                    result["error"] = "2FA প্রয়োজন কিন্তু কী দেওয়া হয়নি। 'none' না লিখে TOTP Secret দিন।"
                    return result
                
                two_factor_id = login_result.get("two_factor_info", {}).get("two_factor_identifier")
                if not two_factor_id:
                    result["error"] = "2FA আইডেন্টিফায়ার পাওয়া যায়নি"
                    return result
                
                if not self._handle_2fa(two_factor_key, two_factor_id):
                    result["error"] = "2FA ভেরিফিকেশন ব্যর্থ। TOTP Secret সঠিক কিনা চেক করুন।"
                    return result
            
            # কেস ৪: চেকপয়েন্ট / চ্যালেঞ্জ
            elif login_result.get("checkpoint_required"):
                result["error"] = "⛔ Instagram চেকপয়েন্ট চাইছে। মোবাইল অ্যাপ থেকে লগইন করে ভেরিফাই করুন।"
                return result
            elif login_result.get("message") == "challenge_required":
                result["error"] = "⛔ Instagram চ্যালেঞ্জ চাইছে। ব্রাউজার থেকে লগইন করে ভেরিফাই করুন।"
                return result
            
            # কেস ৫: ভুল পাসওয়ার্ড
            elif login_result.get("error_type") == "bad_password":
                result["error"] = "❌ ভুল পাসওয়ার্ড। আবার চেষ্টা করুন।"
                return result
            
            # কেস ৬: অন্যান্য এরর
            else:
                error_msg = login_result.get("message", "অজানা")
                result["error"] = f"❌ Instagram লগইন ব্যর্থ: {error_msg}"
                return result
            
            # ========== ধাপ ৪: কুকি সংগ্রহ ==========
            self.log("কুকি সংগ্রহ করা হচ্ছে...")
            time.sleep(1)
            
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
                if cookie.name in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did', 'rur']:
                    important_cookies[cookie.name] = cookie.value
                    self.log(f"  ✅ {cookie.name}: {cookie.value[:25]}...")
            
            # ds_user_id না থাকলে API থেকে নেওয়া
            if 'ds_user_id' not in important_cookies:
                try:
                    user_response = self.session.get(
                        "https://www.instagram.com/api/v1/accounts/current_user/",
                        headers={"X-CSRFToken": self.session.headers.get("X-CSRFToken", "")},
                        timeout=10
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        pk = str(user_data.get("user", {}).get("pk", ""))
                        if pk:
                            important_cookies['ds_user_id'] = pk
                            cookies_dict['ds_user_id'] = pk
                            self.log(f"  ✅ ds_user_id (API): {pk}")
                except:
                    pass
            
            # ফাইনাল চেক
            if 'sessionid' not in important_cookies:
                result["error"] = "❌ sessionid কুকি পাওয়া যায়নি। এক্সট্রাকশন ব্যর্থ।"
                return result
            
            # ========== সফল! ==========
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            
            self.log(f"🎉 সফল! কুকি: {list(important_cookies.keys())}")
            self.log(f"{'='*10} {username} - সফল {'='*10}")
            
        except requests.exceptions.ConnectionError:
            result["error"] = "🔌 কানেকশন এরর। Instagram ব্লক করেছে বা নেটওয়ার্ক সমস্যা।"
        except requests.exceptions.Timeout:
            result["error"] = "⏰ টাইমআউট। Instagram সার্ভার রেসপন্স করছে না।"
        except Exception as e:
            result["error"] = f"💥 এরর: {str(e)[:100]}"
            self.log(f"এক্সেপশন: {e}")
        
        return result
