# instagram.py
import requests
import json
import time
import re
import hashlib
import uuid
import config

class InstagramCookieExtractor:
    """Requests দিয়ে Instagram কুকি এক্সট্রাক্টর (ফিক্সড ভার্সন)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.INSTAGRAM_HEADERS)
        self.current_username = None
        self.device_id = None
    
    def log(self, msg):
        """লগ মেসেজ প্রিন্ট (Railway Logs-এ দেখা যাবে)"""
        print(f"[INSTA] {msg}", flush=True)
    
    def _generate_device_id(self, username):
        """ইউনিক ডিভাইস আইডি জেনারেট"""
        seed = f"android-{username}-{int(time.time())}"
        return "android-" + hashlib.md5(seed.encode()).hexdigest()[:16]
    
    def _get_csrf_token(self):
        """CSRF ও অন্যান্য প্রয়োজনীয় টোকেন সংগ্রহ"""
        try:
            self.log("Instagram হোমপেজ লোড হচ্ছে...")
            
            # ফ্রেশ সেশন দিয়ে হোমপেজ ভিজিট
            response = self.session.get(
                "https://www.instagram.com/",
                headers={
                    "User-Agent": config.INSTAGRAM_HEADERS["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            self.log(f"হোমপেজ স্ট্যাটাস: {response.status_code}")
            
            csrf_token = None
            
            # পদ্ধতি ১: HTML থেকে CSRF খোঁজা
            csrf_match = re.search(r'"csrf_token":"(.*?)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                self.session.headers.update({"X-CSRFToken": csrf_token})
                self.log(f"CSRF (HTML): {csrf_token[:15]}...")
            
            # পদ্ধতি ২: কুকি থেকে CSRF
            if not csrf_token:
                for cookie in self.session.cookies:
                    if cookie.name == 'csrftoken':
                        csrf_token = cookie.value
                        self.session.headers.update({"X-CSRFToken": csrf_token})
                        self.log("CSRF (Cookie) পাওয়া গেছে")
                        break
            
            # পদ্ধতি ৩: API থেকে CSRF
            if not csrf_token:
                self.log("API থেকে CSRF নেওয়ার চেষ্টা...")
                api_response = self.session.get(
                    "https://www.instagram.com/api/v1/web/data/rpc/LXFRXg/",
                    headers={"X-CSRFToken": ""}
                )
                for cookie in self.session.cookies:
                    if cookie.name == 'csrftoken':
                        csrf_token = cookie.value
                        self.session.headers.update({"X-CSRFToken": csrf_token})
                        self.log(f"CSRF (API): {csrf_token[:15]}...")
                        break
            
            if not csrf_token:
                self.log("CSRF টোকেন পাওয়া যায়নি!")
                return None
            
            # ডিভাইস আইডি জেনারেট
            self.device_id = self._generate_device_id(self.current_username or "default")
            
            # গুরুত্বপূর্ণ হেডার সেট
            self.session.headers.update({
                "X-CSRFToken": csrf_token,
                "X-IG-App-ID": "936619743392459",
                "X-IG-App-Locale": "en_US",
                "X-IG-Device-Locale": "en_US",
                "X-IG-Device-ID": self.device_id,
                "X-IG-Connection-Type": "WIFI",
                "X-IG-Capabilities": "3brTv10=",
                "X-IG-Bandwidth-Speed-KBPS": "-1.000",
                "X-IG-Bandwidth-TotalBytes-B": "0",
                "X-IG-Bandwidth-TotalTime-MS": "0",
            })
            
            return csrf_token
            
        except Exception as e:
            self.log(f"CSRF এরর: {e}")
            return None
    
    def _encrypt_password(self, password):
        """Instagram পাসওয়ার্ড এনক্রিপশন"""
        return f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}"
    
    def _handle_2fa(self, two_factor_key, two_factor_identifier):
        """2FA ভেরিফিকেশন হ্যান্ডেল"""
        try:
            # TOTP কোড জেনারেট
            try:
                import pyotp
                clean_key = two_factor_key.replace(" ", "").upper()
                # স্পেস রিমুভ
                clean_key = clean_key.replace(" ", "")
                totp = pyotp.TOTP(clean_key)
                verification_code = totp.now()
                self.log(f"2FA কোড জেনারেট: {verification_code}")
            except Exception as e:
                self.log(f"pyotp এরর: {e}")
                self.log("কী ভুল হতে পারে। ম্যানুয়াল 2FA কোড চেষ্টা করা যায় না।")
                return False
            
            # 2FA ভেরিফিকেশন ডাটা
            two_factor_data = {
                "verification_code": verification_code,
                "two_factor_identifier": two_factor_identifier,
                "username": self.current_username,
                "trust_this_device": "1",
                "verification_method": "3",  # 1=SMS, 2=WhatsApp, 3=TOTP
                "device_id": self.device_id or self._generate_device_id(self.current_username),
                "guid": str(uuid.uuid4()),
                "_csrftoken": self.session.headers.get("X-CSRFToken"),
            }
            
            self.log(f"2FA ডাটা: {json.dumps({k:v for k,v in two_factor_data.items() if k != 'verification_code'})}")
            
            # 2FA API কল
            response = self.session.post(
                "https://www.instagram.com/api/v1/web/accounts/login/ajax/two_factor/",
                data=two_factor_data,
                headers={
                    "X-CSRFToken": self.session.headers.get("X-CSRFToken"),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://www.instagram.com/accounts/login/",
                    "X-IG-App-ID": "936619743392459",
                    "X-Requested-With": "XMLHttpRequest",
                }
            )
            
            self.log(f"2FA স্ট্যাটাস: {response.status_code}")
            self.log(f"2FA রেসপন্স: {response.text[:400]}")
            
            result = response.json()
            
            if result.get("authenticated"):
                self.log("2FA ভেরিফিকেশন সফল!")
                return True
            elif result.get("spam"):
                self.log("2FA স্প্যাম ডিটেক্ট! Instagram ব্লক করেছে।")
                return False
            else:
                self.log(f"2FA ব্যর্থ: {result.get('message', 'অজানা')}")
                return False
                
        except Exception as e:
            self.log(f"2FA এরর: {e}")
            return False
    
    def extract_cookies(self, username, password, two_factor_key=None):
        """
        Instagram থেকে কুকি এক্সট্রাক্ট করা
        
        Args:
            username: Instagram ইউজারনেম
            password: পাসওয়ার্ড
            two_factor_key: TOTP Secret কী (2FA এর জন্য)
            
        Returns:
            dict: রেজাল্ট
        """
        result = {
            "success": False,
            "username": username,
            "cookies": None,
            "important_cookies": None,
            "error": None
        }
        
        self.current_username = username
        self.log(f"========== {username} - শুরু ==========")
        
        try:
            # ধাপ ১: CSRF টোকেন সংগ্রহ
            csrf_token = self._get_csrf_token()
            if not csrf_token:
                result["error"] = "CSRF টোকেন পাওয়া যায়নি। Instagram সার্ভারে কানেক্ট করতে পারেনি।"
                return result
            
            # একটু অপেক্ষা (human-like behaviour)
            time.sleep(3)
            
            # ধাপ ২: লগইন
            self.log(f"লগইন করার চেষ্টা: {username}")
            
            login_data = {
                "username": username,
                "enc_password": self._encrypt_password(password),
                "queryParams": "{}",
                "optIntoOneTap": "false",
                "stopDeletionNonce": "",
                "trustedDeviceRecords": "{}",
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
                }
            )
            
            self.log(f"লগইন স্ট্যাটাস: {login_response.status_code}")
            
            # রেসপন্স পার্স
            try:
                login_result = login_response.json()
            except:
                result["error"] = f"Instagram রেসপন্স পার্স করা যায়নি। স্ট্যাটাস: {login_response.status_code}"
                self.log(f"রেসপন্স: {login_response.text[:300]}")
                return result
            
            self.log(f"লগইন রেসপন্স: {json.dumps(login_result)[:400]}")
            
            # রেজাল্ট চেক
            if login_result.get("authenticated"):
                self.log("✅ লগইন সফল! (কোনো 2FA লাগেনি)")
                
            elif login_result.get("two_factor_required"):
                self.log("2FA প্রয়োজন")
                
                if two_factor_key:
                    two_factor_info = login_result.get("two_factor_info", {})
                    two_factor_id = two_factor_info.get("two_factor_identifier")
                    
                    if not two_factor_id:
                        result["error"] = "2FA আইডেন্টিফায়ার পাওয়া যায়নি"
                        return result
                    
                    self.log(f"2FA মেথড: SMS={two_factor_info.get('sms_two_factor_on')}, TOTP={two_factor_info.get('totp_two_factor_on')}")
                    
                    if not self._handle_2fa(two_factor_key, two_factor_id):
                        result["error"] = "2FA ভেরিফিকেশন ব্যর্থ। TOTP Secret সঠিক কিনা চেক করুন।"
                        return result
                else:
                    result["error"] = "2FA প্রয়োজন কিন্তু আপনি কী দেননি। 'none' না লিখে TOTP Secret দিন।"
                    return result
                    
            elif login_result.get("checkpoint_required"):
                result["error"] = "চেকপয়েন্ট প্রয়োজন। Instagram অ্যাকাউন্ট ভেরিফিকেশন চাইছে। মোবাইল অ্যাপ থেকে লগইন করে ভেরিফাই করুন।"
                return result
                
            elif login_result.get("message") == "challenge_required":
                result["error"] = "চ্যালেঞ্জ প্রয়োজন। Instagram সিকিউরিটি চেক চাইছে।"
                return result
                
            elif login_result.get("error_type") == "bad_password":
                result["error"] = "ভুল পাসওয়ার্ড। সঠিক পাসওয়ার্ড দিন।"
                return result
                
            elif login_result.get("user") == False:
                result["error"] = f"লগইন ব্যর্থ: {login_result.get('message', 'ইউজারনেম বা পাসওয়ার্ড ভুল')}"
                return result
                
            else:
                error_msg = login_result.get("message", "অজানা লগইন এরর")
                result["error"] = f"Instagram: {error_msg}"
                return result
            
            # ধাপ ৩: কুকি সংগ্রহ
            self.log("কুকি সংগ্রহ করা হচ্ছে...")
            time.sleep(2)
            
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
                if cookie.name in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did', 'rur']:
                    important_cookies[cookie.name] = cookie.value
                    self.log(f"✅ {cookie.name} = {cookie.value[:20]}...")
            
            # sessionid চেক
            if 'sessionid' not in important_cookies:
                self.log("সতর্কতা: sessionid পাওয়া যায়নি! কুকি বৈধ নাও হতে পারে।")
                result["error"] = "sessionid পাওয়া যায়নি। এক্সট্রাকশন ব্যর্থ।"
                return result
            
            # ds_user_id চেক
            if 'ds_user_id' not in important_cookies:
                # ds_user_id বের করার চেষ্টা
                try:
                    test_response = self.session.get(
                        "https://www.instagram.com/api/v1/accounts/current_user/",
                        headers={"X-CSRFToken": self.session.headers.get("X-CSRFToken")}
                    )
                    user_data = test_response.json()
                    ds_user_id = str(user_data.get("user", {}).get("pk", ""))
                    if ds_user_id:
                        important_cookies['ds_user_id'] = ds_user_id
                        cookies_dict['ds_user_id'] = ds_user_id
                        self.log(f"ds_user_id API থেকে: {ds_user_id}")
                except:
                    pass
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            
            self.log(f"🎉 সফল! গুরুত্বপূর্ণ কুকি: {list(important_cookies.keys())}")
            self.log(f"========== {username} - সফল ==========")
            
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"কানেকশন এরর: Instagram সার্ভারে কানেক্ট করতে পারেনি। Railway IP ব্লক হতে পারে।"
            self.log(f"কানেকশন এরর: {e}")
        except requests.exceptions.Timeout as e:
            result["error"] = "টাইমআউট! Instagram সার্ভার রেসপন্স করছে না।"
            self.log(f"টাইমআউট: {e}")
        except Exception as e:
            result["error"] = f"সিস্টেম এরর: {str(e)[:100]}"
            self.log(f"এক্সেপশন: {e}")
        
        return result
