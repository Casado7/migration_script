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


def _set_input_value(driver: WebDriver, name: str, value: str) -> bool:
    """Set the value of an input by name. Returns True if set, False otherwise."""
    try:
        el = driver.find_element(By.NAME, name)
        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));", el, value)
        return True
    except Exception:
        return False


def create_test_client(driver: WebDriver, data: dict | None = None, timeout: int = 20) -> Tuple[bool, str]:
    """Fill the Add Client form with fake test data and advance the form.

    - `driver`: active WebDriver on the add-client page
    - `data`: optional dict overriding default fake values

    Returns (success, info). On success `info` is the URL after clicking "Siguiente",
    otherwise it contains an error message.
    """
    defaults = {
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
        "client_address[0].state": "Ciudad de Mexico",
        "client_address[0].city": "Ciudad de Mexico",
        "client_address[0].postal_code": "01234",
        "client_address[0].address": "Av. Test 123",
    }
    if data:
        defaults.update(data)

    # helper to wait for presence of a field name
    def wait_for_name(name: str):
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, name)))
        except TimeoutException:
            return None

    # fill simple inputs
    field_names = [
        "name", "middle_name", "last_name", "mothers_name", "birth", "email",
        "phone", "cellphone",
        "client_address[0].state", "client_address[0].city", "client_address[0].postal_code", "client_address[0].address",
    ]

    for fname in field_names:
        el = wait_for_name(fname)
        if el is None:
            # continue attempting other fields; some forms lazy-load fields
            continue
        try:
            el.clear()
            el.send_keys(defaults.get(fname, ""))
        except Exception:
            # fallback to js-set
            _set_input_value(driver, fname, defaults.get(fname, ""))

    # set hidden/select-ish fields by name (phone_prefix, cellphone_prefix, origin_country, etc.)
    hidden_names = ["phone_prefix", "cellphone_prefix", "origin_country", "nationality", "marital_status", "sex", "client_kind"]
    for h in hidden_names:
        if h in defaults:
            _set_input_value(driver, h, defaults[h])

    # If phone_prefix/cellphone_prefix provided in defaults, set them
    for h in ("phone_prefix", "cellphone_prefix"):
        if h in defaults:
            _set_input_value(driver, h, defaults[h])

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

    # --- Now fill the second tab (Datos Generales) ---
    # Wait for any of the second-tab fields to appear (they are often hidden inputs used by react-select)
    second_tab_names = [
        "origin_country",
        "nationality",
        "marital_status",
        "profession_id",
        "sex",
        "client_kind",
    ]

    def wait_for_any_name(names: list[str], wait: int = timeout):
        try:
            return WebDriverWait(driver, wait).until(lambda d: any(len(d.find_elements(By.NAME, n)) > 0 for n in names))
        except Exception:
            return False

    appeared = wait_for_any_name(second_tab_names, timeout)
    if not appeared:
        # If none of the expected hidden inputs appeared, still return success — form advanced but second tab not detected
        return True, driver.current_url

    # Defaults for second tab values
    second_defaults = {
        "origin_country": "Venezuela",
        "nationality": "Venezolana",
        "marital_status": "Soltero",
        "profession_id": "",
        "sex": "F",
        "client_kind": "M",
    }
    if data:
        # allow overriding second-tab defaults via the same `data` dict
        for k in second_defaults:
            if k in data:
                second_defaults[k] = data[k]

    # set hidden/select-ish second tab fields
    def _set_react_select_value(driver: WebDriver, name: str, value: str) -> bool:
        """Try to set a react-select-like control which has a visible input preceding
        a hidden input with the `name` attribute. Returns True on success."""
        try:
            hidden = driver.find_element(By.NAME, name)
        except Exception:
            return False

        try:
            # find the visible input that is usually the previous sibling or inside the same wrapper
            input_el = driver.execute_script(
                "const hidden = arguments[0];"
                "let container = hidden.previousElementSibling;"
                "if(!container) container = hidden.parentElement && hidden.parentElement.querySelector('.css-b62m3t-container');"
                "if(!container) return null;"
                "const inp = container.querySelector('input');"
                "return inp;",
                hidden,
            )
            if not input_el:
                return False

            try:
                input_el.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].focus();", input_el)
                except Exception:
                    pass

            try:
                input_el.clear()
            except Exception:
                # some react inputs don't support clear(); ignore
                pass

            try:
                input_el.send_keys(value)
                input_el.send_keys(Keys.ENTER)
            except Exception:
                # last resort: set value with JS and dispatch events
                try:
                    driver.execute_script(
                        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true})); arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                        input_el,
                        value,
                    )
                except Exception:
                    return False

            # give JS time to update hidden input/state
            try:
                time.sleep(0.15)
            except Exception:
                pass

            return True
        except Exception:
            return False

    for name, val in second_defaults.items():
        # try react-select style first (visible input + hidden named input)
        try:
            ok = _set_react_select_value(driver, name, val)
            if ok:
                continue
        except Exception:
            pass

        # fallback to setting the hidden input directly
        try:
            _set_input_value(driver, name, val)
        except Exception:
            # ignore individual failures and continue
            pass

    # Some visible text inputs on second tab (e.g., profession may have a visible input placeholder)
    visible_second_fields = ["profession_id"]
    for vf in visible_second_fields:
        try:
            els = driver.find_elements(By.NAME, vf)
            for el in els:
                try:
                    el.clear()
                    el.send_keys(second_defaults.get(vf, ""))
                except Exception:
                    _set_input_value(driver, vf, second_defaults.get(vf, ""))
        except Exception:
            continue

    # final small wait for any JS to process changes
    try:
        time.sleep(0.4)
    except Exception:
        pass

    # After filling second tab, click "Siguiente" again to advance to next step
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
