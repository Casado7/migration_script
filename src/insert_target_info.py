from __future__ import annotations
import os
import time
from dotenv import load_dotenv

from target_helppers.login import start_and_login
from target_helppers.insert_client import navigate_to_add_client_page


def insert_target_info(headless: bool = False, timeout: int = 20) -> None:
    """Start a browser, login to the target app, and (placeholder) insert info.

    Currently this function performs only the login and leaves a TODO where
    insertion logic should go.
    """
    load_dotenv()
    url = os.getenv('TARGET_PAGE_LOGIN_URL')
    if not url:
        print('TARGET_PAGE_LOGIN_URL not set in .env')
        return

    username = os.getenv('TARGET_USERNAME')
    password = os.getenv('TARGET_PASSWORD')
    if not username or not password:
        print('TARGET_USERNAME or TARGET_PASSWORD not set in .env')
        return

    driver, success, info = start_and_login(url, username, password, headless=headless, timeout=timeout)

    if driver is None:
        print('Failed to start driver or navigate:', info)
        return

    if not success:
        print('Login may have failed or stayed on page. Current URL/info:', info)
        # keep the browser open briefly so user can inspect
        time.sleep(2)
        try:
            driver.quit()
        except Exception:
            pass
        return

    # At this point, login succeeded
    print('Login successful, current URL:', info)

    # After successful login, navigate to the add-client page
    nav_success, nav_info = navigate_to_add_client_page(driver)
    if nav_success:
        print('Navigated to add-client page:', nav_info)
    else:
        print('Navigation to add-client page failed:', nav_info)

    # TODO: Add logic here to insert target info after successful login.

    # keep the browser open briefly so user can inspect
    time.sleep(2)
    try:
        driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    insert_target_info(headless=False)
