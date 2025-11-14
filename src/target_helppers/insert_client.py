from __future__ import annotations
import os
import time
from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


# Default test client data used by `create_test_client`.
# Placed here so tests and callers can override or import easily.
TEST_CLIENT_DEFAULTS = {
    "name": "Juan",
    "middle_name": "Perez",
    "last_name": "Perez",
    "mothers_name": "Lopez",
    "birth": "01-01-1990",
    "email": "juan.perez.test+1@example.com",
    "phone_prefix": "52",
    "phone": "5551234567",
    "cellphone_prefix": "52",
    "cellphone": "5512345678",
    # address
    "client_address[0].country": "México",
    "client_address[0].state": "Ciudad de Mexico",
    "client_address[0].city": "Ciudad de Mexico",
    "client_address[0].postal_code": "01234",
    "client_address[0].address": "Av. Test 123",
    # second tab defaults (moved to single test client object)
    "origin_country": "Venezuela",
    "nationality": "Venezolana",
    "marital_status": "Soltero",
    "profession_id": "AMA DE CASA",
    "sex": "F",
    "client_kind": "M",
}


# low-level helpers (moved to helpers.py)
from .helpers import _set_input_value, _set_react_select_value

# tab-specific fillers
from .tabs.personal import fill_personal_tab
from .tabs.general import fill_general_tab
from .tabs.residence import fill_residence_tab


def create_test_client(driver: WebDriver, data: dict | None = None, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the Add Client form with fake test data and advance the form.

    - `driver`: active WebDriver on the add-client page
    - `data`: optional dict overriding default fake values

    Returns (success, info). On success `info` is the URL after clicking "Siguiente",
    otherwise it contains an error message.
    """
    # Start from module-level defaults; allow caller override via `data`.
    defaults = TEST_CLIENT_DEFAULTS.copy()
    if data:
        defaults.update(data)

    # Fill personal tab (name, emails, phones, prefixes) using the tab filler
    try:
        ok_personal, msg_personal = fill_personal_tab(driver, defaults, timeout)
    except Exception:
        ok_personal, msg_personal = False, "exception in fill_personal_tab"
    # proceed regardless — fillers are best-effort and create_test_client will continue

    # click the "Siguiente" button (card-footer)
    def _click_siguiente(timeout_sec: int = timeout) -> bool:
        try:
            btn = WebDriverWait(driver, timeout_sec).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form .card-footer button.btn-primary"))
            )
        except Exception:
            return False

        try:
            # make sure element is in view
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            except Exception:
                pass

            # If normal click works, prefer it
            try:
                if btn.is_displayed():
                    btn.click()
                else:
                    # element may be present but hidden; try JS click
                    driver.execute_script("arguments[0].click();", btn)
            except Exception:
                # fallback: dispatch a MouseEvent (some apps require real mouse event)
                try:
                    driver.execute_script(
                        "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));",
                        btn,
                    )
                except Exception:
                    # last resort: direct click via JS
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                    except Exception:
                        return False

            return True
        except Exception:
            return False

    clicked = _click_siguiente()
    if not clicked:
        return False, "Could not click 'Siguiente' button (all strategies failed)"

    # wait briefly for navigation or DOM change
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except Exception:
        time.sleep(0.5)

    # Fill the second tab (Datos Generales) using the dedicated filler
    try:
        ok_general, msg_general = fill_general_tab(driver, defaults, timeout)
    except Exception:
        ok_general, msg_general = False, "exception in fill_general_tab"

    # After filling second tab, click "Siguiente" to advance
    try:
        clicked2 = _click_siguiente()
    except Exception:
        clicked2 = False

    if not clicked2:
        return False, "Could not click 'Siguiente' on second tab"

    # wait for navigation/DOM update after second click
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except Exception:
        time.sleep(0.5)

    # Press "Siguiente" two more times (user requested skipping next two tabs)
    for attempt in range(1, 3):
        try:
            ok = _click_siguiente()
        except Exception:
            ok = False

        if not ok:
            return False, f"Could not click 'Siguiente' on subsequent step #{attempt}"

        # small wait after each click to allow DOM updates
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        except Exception:
            time.sleep(0.5)

    # Fill residence tab using dedicated filler
    try:
        ok_res, msg_res = fill_residence_tab(driver, defaults, timeout)
    except Exception:
        ok_res, msg_res = False, "exception in fill_residence_tab"

    return True, driver.current_url


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
