from __future__ import annotations
import os
import time
from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


def navigate_to_add_client_page(driver: WebDriver, url: str | None = None, timeout: int = 20) -> Tuple[bool, str]:
    """Navigate the given WebDriver to the target 'add client' page.

    If `url` is None, reads `TARGET_PAGE_ADD_CLIENT_URL` from environment.
    Returns (success, info) where `success` is True if navigation completed
    and `info` is the current URL or an error message.
    """
    if url is None:
        url = os.getenv('TARGET_PAGE_ADD_CLIENT_URL')
        if not url:
            return False, 'TARGET_PAGE_ADD_CLIENT_URL not set in environment'

    try:
        driver.get(url)
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            # fallback short sleep
            time.sleep(1)
        return True, driver.current_url
    except Exception as e:
        return False, f'Error navigating to add-client page: {e}'
