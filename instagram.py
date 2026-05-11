from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pickle
import time
import os

def extract_cookies(username, password, two_factor_code):
    driver = webdriver.Chrome(executable_path="chromedriver.exe")
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    # Input username
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(5)

    # Handle 2FA
    if "verificationCode" in driver.page_source:
        driver.find_element(By.NAME, "verificationCode").send_keys(two_factor_code)
        driver.find_element(By.NAME, "verificationCode").send_keys(Keys.RETURN)
        time.sleep(5)

    # Save cookies
    os.makedirs("cookies", exist_ok=True)
    with open(f"cookies/{username}_cookies.pkl", "wb") as f:
        pickle.dump(driver.get_cookies(), f)

    driver.quit()
    print(f"Cookies saved successfully for {username}!")
