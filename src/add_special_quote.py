from __future__ import annotations
import os
import time
from dotenv import load_dotenv

from target_helppers.login import start_and_login


def add_special_quote(headless: bool = False, timeout: int = 20) -> None:
    """Login to target app and navigate to special-quote URL (minimal flow).

    Uses environment variables:
    - TARGET_PAGE_LOGIN_URL
    - TARGET_USERNAME
    - TARGET_PASSWORD
    - TARGET_PAGE_ADD_SPECIAL_QUOTE_URL
    """
    load_dotenv()
    login_url = os.getenv('TARGET_PAGE_LOGIN_URL')
    if not login_url:
        print('TARGET_PAGE_LOGIN_URL not set in .env')
        return

    username = os.getenv('TARGET_USERNAME')
    password = os.getenv('TARGET_PASSWORD')
    if not username or not password:
        print('TARGET_USERNAME or TARGET_PASSWORD not set in .env')
        return

    driver, success, info = start_and_login(login_url, username, password, headless=headless, timeout=timeout)

    if driver is None:
        print('Failed to start driver or navigate:', info)
        return

    if not success:
        print('Login may have failed or stayed on page. Current URL/info:', info)
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass
        return

    print('Login successful, current URL:', info)

    target_url = os.getenv('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL')
    if not target_url:
        print('TARGET_PAGE_ADD_SPECIAL_QUOTE_URL not set in .env')
        try:
            driver.quit()
        except Exception:
            pass
        return

    try:
        print('Navigating to special-quote page:', target_url)
        driver.get(target_url)
        time.sleep(2)
        print('Current URL after navigate:', driver.current_url)
    except Exception as e:
        print('Error navigating to special-quote URL:', e)

    # keep browser open briefly for inspection
    time.sleep(2)
    try:
        driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    add_special_quote(headless=False)
