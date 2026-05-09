# instagram.py
import json
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, TwoFactorRequired

class InstagramCookieExtractor:
    """Instagrapi দিয়ে Instagram কুকি এক্সট্রাক্টর"""
    
    def __init__(self):
        self.client = Client()
    
    def log(self, msg):
        print(f"[INSTA] {msg}", flush=True)
    
    def extract_cookies(self, username, password, two_factor_key=None):
        """
        Instagram থেকে কুকি এক্সট্রাক্ট
        
        Args:
            username: ইউজারনেম
            password: পাসওয়ার্ড
            two_factor_key: ৬-ডিজিট ম্যানুয়াল কোড
            
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
        
        self.log(f"{'='*10} {username} - শুরু {'='*10}")
        
        try:
            # 2FA হ্যান্ডলার
            verification_code = None
            
            if two_factor_key:
                if two_factor_key.strip().isdigit() and len(two_factor_key.strip()) == 6:
                    verification_code = two_factor_key.strip()
                    self.log(f"ম্যানুয়াল 2FA কোড: {verification_code}")
                else:
                    try:
                        import pyotp
                        clean_key = two_factor_key.replace(" ", "").upper()
                        totp = pyotp.TOTP(clean_key)
                        verification_code = totp.now()
                        self.log(f"TOTP কোড: {verification_code}")
                    except:
                        pass
            
            # লগইন
            self.log(f"লগইন চেষ্টা: {username}")
            
            if verification_code:
                self.client.login(username, password, verification_code=verification_code)
            else:
                self.client.login(username, password)
            
            self.log("✅ লগইন সফল!")
            
            # কুকি বের করা
            self.log("কুকি সংগ্রহ...")
            settings = self.client.get_settings()
            
            cookies_dict = {}
            important_cookies = {}
            
            # Authorization header থেকে token
            auth_token = settings.get('authorization_data', {}).get('sessionid', '')
            
            # Cookies
            cookies_raw = self.client.private.cookies
            for key, value in cookies_raw.items():
                cookies_dict[key] = value
            
            # গুরুত্বপূর্ণ কুকি
            for key in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did']:
                if key in cookies_dict:
                    important_cookies[key] = cookies_dict[key]
                    self.log(f"  ✅ {key}: {cookies_dict[key][:25]}...")
            
            # ds_user_id
            try:
                user_id = self.client.user_id
                important_cookies['ds_user_id'] = str(user_id)
                cookies_dict['ds_user_id'] = str(user_id)
                self.log(f"  ✅ ds_user_id: {user_id}")
            except:
                pass
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            
            self.log(f"🎉 সফল!")
            
        except TwoFactorRequired:
            result["error"] = "2FA কোড প্রয়োজন। দয়া করে ৬-ডিজিট 2FA কোড দিন।"
            self.log("2FA প্রয়োজন")
            
        except ChallengeRequired:
            result["error"] = "Instagram চ্যালেঞ্জ চাইছে। মোবাইল অ্যাপ থেকে ভেরিফাই করুন।"
            self.log("চ্যালেঞ্জ প্রয়োজন")
            
        except LoginRequired:
            result["error"] = "লগইন ব্যর্থ। ইউজারনেম বা পাসওয়ার্ড ভুল।"
            self.log("লগইন ব্যর্থ")
            
        except Exception as e:
            result["error"] = f"এরর: {str(e)[:100]}"
            self.log(f"এক্সেপশন: {e}")
        
        return result
