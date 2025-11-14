from __future__ import annotations
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


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
        print('Page loaded (or timeout reached). You can now inspect the browser.')
        # keep the browser open briefly so user can verify (adjust if you want immediate close)
        time.sleep(2)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    # Run non-headless by default so you can see the page
    open_target_login(headless=True)
