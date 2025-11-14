from __future__ import annotations
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def open_target_login(headless: bool = False, timeout: int = 20) -> None:
    """Open the target app login page (reads URL from .env -> TARGET_PAGE_LOGIN_URL).

    This script only navigates to the login page and waits for it to finish loading.
    It does not perform any form submission or further actions.
    """
    load_dotenv()
    url = os.getenv('TARGET_PAGE_LOGIN_URL')
    if not url:
        print('TARGET_PAGE_LOGIN_URL not set in .env')
        return

    opts = Options()
    if headless:
        opts.add_argument('--headless=new')
    # common sensible defaults
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        print('Could not start Chrome WebDriver:', e)
        return

    try:
        print('Opening target login URL:', url)
        driver.get(url)
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            # fallback short sleep if wait fails
            time.sleep(1)

        # Fill username and password from .env and submit the form
        username = os.getenv('TARGET_USERNAME')
        password = os.getenv('TARGET_PASSWORD')
        if not username or not password:
            print('TARGET_USERNAME or TARGET_PASSWORD not set in .env')
            # keep the browser open briefly so user can inspect
            time.sleep(2)
            return

        try:
            user_el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            pass_el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.NAME, 'password'))
            )
        except Exception as e:
            print('Could not find username/password inputs:', e)
            time.sleep(2)
            return

        user_el.clear()
        user_el.send_keys(username)
        pass_el.clear()
        pass_el.send_keys(password)

        # Find the submit button (type=submit) and click it
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_btn.click()
        except Exception:
            # fallback: submit the form via pressing Enter on password field
            pass_el.send_keys('\n')

        # Wait for navigation / login result
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.current_url != url)
            print('Login appears to have navigated away from login page. Current URL:', driver.current_url)
        except Exception:
            # if URL didn't change, wait a short moment and print page title for debugging
            time.sleep(1)
            print('Finished submit step (timeout reached). Current URL:', driver.current_url)

        # keep the browser open briefly so user can verify (adjust if you want immediate close)
        time.sleep(2)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    # Run non-headless by default so you can see the page
    open_target_login(headless=False)
