from __future__ import annotations
import time
from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def fill_and_submit_login(driver: WebDriver, username: str, password: str, timeout: int = 20) -> Tuple[bool, str]:
    """Fill username/password on the current page (assumed to be the login page) and submit.

    Returns a tuple (success, info) where `success` is True if navigation away from the
    login URL was detected within `timeout` seconds, and `info` contains either the
    new URL or an error message for debugging.
    """
    original_url = driver.current_url
    try:
        user_el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        pass_el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
    except Exception as e:
        return False, f"Could not find username/password inputs: {e}"

    try:
        user_el.clear()
        user_el.send_keys(username)
        pass_el.clear()
        pass_el.send_keys(password)

        # Try clicking a submit button first, otherwise send Enter on password
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_btn.click()
        except Exception:
            pass_el.send_keys("\n")

        try:
            WebDriverWait(driver, timeout).until(lambda d: d.current_url != original_url)
            return True, driver.current_url
        except Exception:
            # Not necessarily an error — maybe the app shows inline errors.
            time.sleep(0.5)
            return False, driver.current_url
    except Exception as e:
        return False, f"Error during login attempt: {e}"


def start_and_login(url: str, username: str, password: str, headless: bool = False, timeout: int = 20):
    """Start a Chrome WebDriver, navigate to `url`, and perform login.

    Returns a tuple `(driver, success, info)` where `driver` is the WebDriver instance
    (or `None` if it couldn't be created), `success` is the boolean result from the
    login attempt, and `info` contains either the new URL or an error message.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait

    opts = Options()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')

    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        return None, False, f'Could not start Chrome WebDriver: {e}'

    try:
        driver.get(url)
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            time.sleep(1)

        success, info = fill_and_submit_login(driver, username, password, timeout=timeout)
        return driver, success, info
    except Exception as e:
        try:
            driver.quit()
        except Exception:
            pass
        return None, False, f'Error during navigation/login: {e}'
