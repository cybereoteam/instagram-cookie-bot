# instagram.py
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class InstagramCookieExtractor:
    """Selenium দিয়ে Instagram কুকি এক্সট্রাক্টর"""
    
    def __init__(self):
        self.driver = None
    
    def log(self, msg):
        print(f"[INSTA] {msg}", flush=True)
    
    def _setup_driver(self):
        """Chrome ড্রাইভার সেটআপ"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # ব্যাকগ্রাউন্ডে চলবে
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service('/data/data/com.termux/files/usr/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def _random_delay(self, min_sec=1, max_sec=3):
        """র‍্যান্ডম ডিলে"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def extract_cookies(self, username, password, two_factor_key=None):
        """
        Instagram থেকে কুকি এক্সট্রাক্ট
        
        Args:
            username: ইউজারনেম
            password: পাসওয়ার্ড
            two_factor_key: TOTP Secret বা ৬-ডিজিট কোড
            
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
            # ড্রাইভার সেটআপ
            self._setup_driver()
            
            # Instagram খোলা
            self.log("Instagram খোলা হচ্ছে...")
            self.driver.get("https://www.instagram.com/accounts/login/")
            self._random_delay(3, 5)
            
            # ইউজারনেম
            self.log("ইউজারনেম দেওয়া হচ্ছে...")
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            for char in username:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            self._random_delay(1, 2)
            
            # পাসওয়ার্ড
            self.log("পাসওয়ার্ড দেওয়া হচ্ছে...")
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            self._random_delay(1, 2)
            
            # লগইন বাটন
            self.log("লগইন বাটনে ক্লিক...")
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            self._random_delay(5, 8)
            
            # 2FA চেক
            current_url = self.driver.current_url
            
            if "challenge" in current_url or "two_factor" in current_url:
                self.log("2FA প্রয়োজন")
                
                if two_factor_key:
                    # 2FA কোড তৈরি
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
                            result["error"] = "2FA কোড জেনারেট করতে ব্যর্থ"
                            return result
                    
                    # কোড ইনপুট
                    code_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@name='verificationCode' or @aria-label='Security code']"))
                    )
                    code_field.clear()
                    code_field.send_keys(verification_code)
                    self._random_delay(1, 2)
                    
                    # সাবমিট
                    submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Confirm')]")
                    submit_btn.click()
                    self._random_delay(5, 8)
                    
                    # চেক
                    if "challenge" in self.driver.current_url or "two_factor" in self.driver.current_url:
                        result["error"] = "2FA ভেরিফিকেশন ব্যর্থ"
                        return result
                else:
                    result["error"] = "2FA প্রয়োজন কিন্তু কী দেওয়া হয়নি"
                    return result
            
            # লগইন চেক
            if "login" in self.driver.current_url:
                result["error"] = "লগইন ব্যর্থ"
                return result
            
            self.log("লগইন সফল!")
            self._random_delay(2, 3)
            
            # কুকি সংগ্রহ
            self.log("কুকি সংগ্রহ...")
            cookies = self.driver.get_cookies()
            
            cookies_dict = {}
            important_cookies = {}
            
            for cookie in cookies:
                cookies_dict[cookie['name']] = cookie['value']
                if cookie['name'] in ['sessionid', 'csrftoken', 'ds_user_id', 'mid', 'ig_did', 'rur']:
                    important_cookies[cookie['name']] = cookie['value']
                    self.log(f"  {cookie['name']}: {cookie['value'][:25]}...")
            
            if 'sessionid' not in important_cookies:
                result["error"] = "sessionid পাওয়া যায়নি"
                return result
            
            result["success"] = True
            result["cookies"] = cookies_dict
            result["important_cookies"] = important_cookies
            
            self.log(f"সফল! কুকি: {list(important_cookies.keys())}")
            self.log(f"{'='*10} {username} - সফল {'='*10}")
            
        except Exception as e:
            result["error"] = f"এরর: {str(e)[:100]}"
            self.log(f"এক্সেপশন: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return result
