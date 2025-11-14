from __future__ import annotations
import os
import time
from typing import Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


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
        "middle_name": "P.",
        "last_name": "Perez",
        "mothers_name": "Lopez",
        "birth": "1990-01-01",
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
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form .card-footer button.btn-primary"))
        )
        btn.click()
    except Exception as e:
        return False, f"Could not click 'Siguiente' button: {e}"

    # wait briefly for navigation or DOM change
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
